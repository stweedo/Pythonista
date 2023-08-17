import clipboard
import keyboard

# Get text from the clipboard
text = clipboard.get()

# Output the text to the active field
keyboard.insert_text(text)
