import clipboard
import console
import json
import os
import ui
import random


class ClipboardBuffer:
    FILENAME = 'clipboard_buffer.json'
    MAX_SIZE = 10

    def __init__(self):
        self.buffer = self._load()

    def _load(self):
        if os.path.exists(self.FILENAME):
            with open(self.FILENAME, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def save(self):
        with open(self.FILENAME, 'w') as f:
            json.dump(self.buffer, f)

    def add(self, text):
        if len(self.buffer) < self.MAX_SIZE and text not in self.buffer:
            self.buffer.append(text)
            self.save()
            return True
        return False

    def clear(self):
        self.buffer = []
        self.save()


def show_alert(message):
    try:
        ui.alert(message)
    except AttributeError:
        console.hud_alert(message)


def import_clipboard(sender):
    text = clipboard.get()
    if len(clipboard_buffer.buffer) >= clipboard_buffer.MAX_SIZE:
        show_alert('Clipboard buffer is full')
        return
    if text in clipboard_buffer.buffer:
        show_alert('Item already exists in the clipboard buffer')
        return
    if clipboard_buffer.add(text):
        show_alert('Clipboard has been updated')

def view_clipboard(sender):
    def table_tapped(sender):
        if sender.selected_row is not None:
            item = clipboard_buffer.buffer[sender.selected_row]
            clipboard.set(item)
            show_alert('Clipboard updated with selected item')

    def generate_dark_color():
		    while True:
		        red = random.uniform(0, 0.7)
		        green = random.uniform(0, 0.6)  # Limiting green a bit more because of its dominance in luminance
		        blue = random.uniform(0, 0.7)
		
		        luminance = 0.299 * red + 0.587 * green + 0.114 * blue
		
		        if luminance < 0.5:
		            break
		
		    return (red, green, blue)
		
    def tableview_cell_for_row(tableview, section, row):
		    cell = ui.TableViewCell('subtitle')
		    cell.text_label.number_of_lines = 0
		    displayed_text = clipboard_buffer.buffer[row][:100] + ('...' if len(clipboard_buffer.buffer[row]) > 100 else '')
		    cell.text_label.text = displayed_text
		
		    cell.background_color = generate_dark_color()
		    cell.text_label.text_color = 'white'
		    return cell

    def tableview_delete(tableview, section, row):
        del clipboard_buffer.buffer[row]
        clipboard_buffer.save()
        tableview.data_source.items = clipboard_buffer.buffer
        tableview.reload()

    if not clipboard_buffer.buffer:
        show_alert('No saved clipboards')
        return

    data_source = ui.ListDataSource(clipboard_buffer.buffer)
    data_source.tableview_cell_for_row = tableview_cell_for_row
    data_source.action = table_tapped
    data_source.tableview_can_delete = lambda tableview, section, row: True
    data_source.tableview_delete = tableview_delete

    table_view = ui.TableView()
    table_view.data_source = data_source
    table_view.delegate = data_source
    table_view.present('sheet')


def clear_all(sender):
    clipboard_buffer.clear()
    show_alert("Cleared all items from the clipboard buffer")


def create_button(title, action, bg_color):
    button = ui.Button(title=title, action=action)
    button.background_color = bg_color
    button.tint_color = 'white'
    button.corner_radius = 10
    button.width = 200
    button.height = 50
    return button


def add_and_position_buttons():
    buttons = [
        ('Import Clipboard', import_clipboard, 'blue'),
        ('View Saved Clipboards', view_clipboard, 'green'),
        ('Clear All', clear_all, 'red')
    ]

    prev_button_frame = (0, 0, 0, 0)
    for title, action, color in buttons:
        button = create_button(title, action, color)
        space_between = (view.height - (3 * button.height)) / 4
        button.frame = (view.width / 2 - 100, prev_button_frame[1] + prev_button_frame[3] + space_between, 200, 50)
        view.add_subview(button)
        prev_button_frame = button.frame


console.clear()
clipboard_buffer = ClipboardBuffer()
view = ui.View(bg_color='white')
view.present("sheet")
add_and_position_buttons()
