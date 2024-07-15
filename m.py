import os
import re
import subprocess
import telebot
from threading import Timer
import time
from io import BytesIO
import cairosvg
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the bot with the token from environment variable
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN provided in environment variables")

bot = telebot.TeleBot(TOKEN)

# List of authorized user IDs
AUTHORIZED_USERS = [5113311276, 6800732852]  # Replace with actual user chat IDs

# Regex pattern to match the IP, port, and duration
pattern = re.compile(r"(\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)\s(\d{1,5})\s(\d+)")

# Dictionary to keep track of subprocesses and timers
processes = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 *Welcome to the Action Bot!*\n\n"
        "To initiate an action, please send a message in the format:\n"
        "`<ip> <port> <duration>`\n\n"
        "To stop all ongoing actions, send:\n"
        "`stop all`\n\n"
        "🔐 *Note:* Only authorized users can use this bot in private chat."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['userinfo'])
def user_info(message):
    user = message.from_user
    user_info_text = (
        f"📝 *User Info:*\n\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"👤 *Name:* `{user.first_name} {user.last_name}`\n"
        f"🔖 *Username:* @{user.username}\n"
        f"📸 *Profile Photos:* `Not Available`\n"
        f"🔄 *Previous Names:* `Not Available`\n"
    )
    bot.reply_to(message, user_info_text, parse_mode='Markdown')

@bot.message_handler(commands=['list'])
def list_actions(message):
    if not processes:
        bot.reply_to(message, 'No active actions.', parse_mode='Markdown')
        return

    actions_list = "🔧 *Active Actions:*\n\n"
    for pid, process_info in processes.items():
        actions_list += (
            f"🆔 *Process ID:* {pid}\n"
            f"🌐 *IP:* {process_info['ip']}\n"
            f"🔢 *Port:* {process_info['port']}\n"
            f"⏳ *Duration:* {process_info['duration']} seconds\n\n"
        )
    bot.reply_to(message, actions_list, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_type = message.chat.type
    
    if chat_type == 'private' and user_id not in AUTHORIZED_USERS:
        bot.reply_to(message, '❌ *You are not authorized to use this bot.*', parse_mode='Markdown')
        return

    text = message.text.strip().lower()
    if text == 'stop all':
        stop_all_actions(message)
        return

    match = pattern.match(text)
    if match:
        ip, port, duration = match.groups()
        
        # Generate an SVG image for the starting message
        svg_content = f"""
        <svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#0078D7;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#00A4EF;stop-opacity:1" />
                </linearGradient>
                <style>
                    .title {{ font: bold 24px sans-serif; fill: white; }}
                    .text {{ font: 18px sans-serif; fill: white; }}
                </style>
            </defs>
            <rect width="300" height="200" fill="url(#grad1)"/>
            <text x="10" y="40" class="title">🚀 Starting Action...</text>
            <text x="10" y="80" class="text">IP: {ip}</text>
            <text x="10" y="110" class="text">Port: {port}</text>
            <text x="10" y="140" class="text">Duration: {duration} seconds</text>
        </svg>
        """

        try:
            # Convert the SVG content to PNG
            png_image = cairosvg.svg2png(bytestring=svg_content)
            image_file = BytesIO(png_image)
            image_file.seek(0)

            # Send the starting message as an image
            bot.send_photo(message.chat.id, image_file, caption="🚀 *Action started!*", parse_mode='Markdown')

            # Run the action command
            full_command = f"./action {ip} {port} {duration} 400"
            process = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processes[process.pid] = {'process': process, 'ip': ip, 'port': port, 'duration': duration}
            
            # Schedule a timer to check process status
            timer = Timer(int(duration), check_process_status, [message, process, ip, port, duration])
            timer.start()

            logging.info(f"Started action: IP={ip}, Port={port}, Duration={duration}")

        except Exception as e:
            logging.error(f"Error starting action: {e}")
            bot.reply_to(message, f"❌ *Error starting action:* {str(e)}", parse_mode='Markdown')
    else:
        bot.reply_to(message, (
            "❌ *Invalid format.* Please use the format:\n"
            "`<ip> <port> <duration>`"
        ), parse_mode='Markdown')

def check_process_status(message, process, ip, port, duration):
    try:
        # Check if the process has completed
        return_code = process.poll()
        if return_code is None:
            # Process is still running, terminate it
            process.terminate()
            process.wait()
        
        # Remove process from tracking dictionary
        processes.pop(process.pid, None)

        # Generate an SVG image for the success message
        svg_content = f"""
        <svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#34C759;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#32D74B;stop-opacity:1" />
                </linearGradient>
                <style>
                    .title {{ font: bold 24px sans-serif; fill: white; }}
                    .text {{ font: 18px sans-serif; fill: white; }}
                    .footer {{ font: 14px sans-serif; fill: white; }}
                </style>
            </defs>
            <rect width="300" height="200" fill="url(#grad2)"/>
            <text x="10" y="40" class="title">✅ Action Complete!</text>
            <text x="10" y="80" class="text">IP: {ip}</text>
            <text x="10" y="110" class="text">Port: {port}</text>
            <text x="10" y="140" class="text">Duration: {duration} seconds</text>
            <text x="10" y="170" class="footer">Check log for details.</text>
        </svg>
        """
        
        png_image = cairosvg.svg2png(bytestring=svg_content)
        image_file = BytesIO(png_image)
        image_file.seek(0)

        bot.send_photo(message.chat.id, image_file, caption="✅ *Action complete!*", parse_mode='Markdown')

        logging.info(f"Action complete: IP={ip}, Port={port}, Duration={duration}")

    except Exception as e:
        logging.error(f"Error checking process status: {e}")
        bot.reply_to(message, f"❌ *Error completing action:* {str(e)}", parse_mode='Markdown')

def stop_all_actions(message):
    for pid, process_info in processes.items():
        try:
            process_info['process'].terminate()
            process_info['process'].wait()
        except Exception as e:
            logging.error(f"Error stopping process {pid}: {e}")
    
    processes.clear()
    bot.reply_to(message, "🛑 *All actions have been stopped.*", parse_mode='Markdown')

# Polling to keep the bot running
bot.polling(none_stop=True)
