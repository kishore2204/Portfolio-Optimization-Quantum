"""Remove emoji and special Unicode characters from main.py and config_constants.py"""

import re

files_to_clean = ['main.py', 'config_constants.py']

replacements = {
    '📋': '[PLAN]',
    '🔄': '[REBALANCE]',
    '📊': '[DATA]',
    '⚛️': '[QUANTUM]',
    '🏆': '[BEST]',
    '💰': '[BUDGET]',
    '🎖️': '[INSIGHT]',
    '🎯': '[TARGET]',
    '✅': '[OK]',
    '💾': '[SAVE]',
    '🎨': '[VISUAL]',
    '📁': '[CHECK]',
    '🔍': '[CHECK]',
    '└─': '  -',
    '├─': '  -',
    '│': '|',
    '├': '+',
    '└': '+',
    '•': '*',
    '═': '=',
    '✓': '[OK]',
}

for filename in files_to_clean:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply replacements
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Cleaned {filename}")
    except Exception as e:
        print(f"✗ Error cleaning {filename}: {e}")

print("\nCleanup complete!")
