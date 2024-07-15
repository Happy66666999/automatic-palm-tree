import os
import re
import subprocess
import telebot
from threading import Timer
import time
import base64

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

# Function to generate SVG content and save it as a file
def generate_svg(content, color, fill, filename):
    svg_content = f'''
    <svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="40" stroke="{color}" stroke-width="4" fill="{fill}" />
        <text x="50%" y="50%" text-anchor="middle" fill="black" font-size="20px" font-family="Arial" dy=".3em">{content}</text>
    </svg>
    '''
    with open(filename, 'w') as file:
        file.write(svg_content)

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
        
        bot.reply_to(message, (
            f"🚀 *Starting action...*\n\n"
            f"📡 *IP:* `{ip}`\n"
            f"🔌 *Port:* `{port}`\n"
            f"⏱ *Duration:* `{duration} seconds`\n"
        ), parse_mode='Markdown')
        
        # Run the action command
        full_command = f"./action {ip} {port} {duration} 400"
        process = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes[process.pid] = process
        
        # Schedule a timer to check process status
        timer = Timer(int(duration), check_process_status, [message, process, ip, port, duration])
        timer.start()
    else:
        bot.reply_to(message, (
            "❌ *Invalid format.* Please use the format:\n"
            "`<ip> <port> <duration>`"
        ), parse_mode='Markdown')

def check_process_status(message, process, ip, port, duration):
    # Check if the process has completed
    return_code = process.poll()
    if return_code is None:
        # Process is still running, terminate it
        process.terminate()
        process.wait()
    
    # Remove process from tracking dictionary
    processes.pop(process.pid, None)

    # Generate SVG for action completed
    svg_filename = 'success.svg'
    generate_svg('Success', 'blue', 'lightblue', svg_filename)

    # Action succeeded
    with open(svg_filename, 'rb') as svg_file:
        bot.send_photo(message.chat.id, svg_file, caption=(
            f"✅ *Action completed successfully!*\n\n"
            f"📡 *Target IP:* `{ip}`\n"
            f"🔌 *Port:* `{port}`\n"
            f"⏱ *Duration:* `{duration} seconds`\n\n"
            f"_By Ibraheem_"
        ), parse_mode='Markdown')

def stop_all_actions(message):
    for pid, process in list(processes.items()):
        process.terminate()
        process.wait()
        processes.pop(pid, None)
    bot.reply_to(message, '🛑 *All actions have been stopped.*', parse_mode='Markdown')

# Start polling
bot.polling()
