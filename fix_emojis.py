#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix emoji encoding issues in Dashboard.js"""

import sys

# Read the file with UTF-8 encoding
with open('Frontend/src/components/Dashboard.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Map of garbled emojis to correct emojis
replacements = {
    'ðŸ"„': '📄',  # document
    'ðŸ"': '📁',    # folder
    'ðŸ"‹': '📋',    # clipboard
    'ðŸ"‚': '📂',    # open folder
    'ðŸ"´': '🔴',    # red circle
    'ðŸ—'ï¸': '🗑️',  # trash
    'ðŸ'¥': '👥',    # people
    'ðŸ'¤': '👤',    # person
    'ðŸ¤–': '🤖',    # robot
    'ðŸ§ ': '🧠',    # brain
    'ðŸ•'': '🕒',    # clock
    'ðŸ"Š': '📊',    # chart
    'ðŸŽ¤': '🎤',    # microphone
    'ðŸ"§': '🔧',    # wrench
    'ðŸ¦·': '🦷',    # tooth
}

# Apply replacements
for garbled, correct in replacements.items():
    content = content.replace(garbled, correct)

# Write back with UTF-8 encoding (no BOM)
with open('Frontend/src/components/Dashboard.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed emoji encoding successfully!")
print(f"Applied {len(replacements)} emoji replacements")
