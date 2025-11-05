import codecs

# Read file
with open('Frontend/src/components/Dashboard.js', 'rb') as f:
    content = f.read()

# Decode as UTF-8
text = content.decode('utf-8', errors='ignore')

# Fix common emoji encoding issues by replacing byte sequences
text = text.replace('\udcf0\udc9f\udc93\udc84', '📄')  # document
text = text.replace('\udcf0\udc9f\udc93\udc81', '📁')  # folder  
text = text.replace('\udcf0\udc9f\udc93\udc8b', '📋')  # clipboard
text = text.replace('\udcf0\udc9f\udc93\udc82', '📂')  # open folder
text = text.replace('\udcf0\udc9f\udc94\udcb4', '🔴')  # red circle
text = text.replace('\udcf0\udc9f\udc91\udca5', '👥')  # people
text = text.replace('\udcf0\udc9f\udc91\udca4', '👤')  # person
text = text.replace('\udcf0\udc9f\udca4\udc96', '🤖')  # robot
text = text.replace('\udcf0\udc9f\udca7\udca0', '🧠')  # brain
text = text.replace('\udcf0\udc9f\udc95\udc92', '🕒')  # clock
text = text.replace('\udcf0\udc9f\udc93\udc8a', '📊')  # chart
text = text.replace('\udcf0\udc9f\udc8e\udca4', '🎤')  # microphone
text = text.replace('\udcf0\udc9f\udc94\udca7', '🔧')  # wrench
text = text.replace('\udcf0\udc9f\udca6\udcb7', '🦷')  # tooth

# Write back
with open('Frontend/src/components/Dashboard.js', 'wb') as f:
    f.write(text.encode('utf-8'))

print('Fixed emojis!')
