import clipboard
import console
import json
import os
import ui
import random
from pathlib import Path

# --- Constants ---
BUFFER_FILENAME = 'clipboard_buffer.json'
BUFFER_MAX_SIZE = 10
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50
BUTTON_CORNER_RADIUS = 10
BUTTON_SPACING = 15
KEYBOARD_TOP_BAR_HEIGHT = 40
KEYBOARD_MENU_BUTTON_PADDING = 10

# Improved keyboard layout constants
KEYBOARD_MODE_BUTTON_HEIGHT = 45
KEYBOARD_MODE_BUTTON_SPACING = 12
KEYBOARD_BUTTON_MIN_WIDTH = 180  # Minimum button width to prevent too narrow buttons

# UI Colors
COLOR_BG_MAIN = '#FFFFFF'
COLOR_BUTTON_IMPORT_BG = '#007AFF'
COLOR_BUTTON_VIEW_BG = '#4CD964'
COLOR_BUTTON_CLEAR_BG = '#FF3B30'
COLOR_BUTTON_BACK_BG = '#8E8E93'
COLOR_BUTTON_TINT = '#FFFFFF'
COLOR_TABLE_CELL_BG = '#333333'
COLOR_TABLE_CELL_TEXT = '#FFFFFF'
COLOR_TABLE_CELL_SELECT_BG = '#555555'


class ClipboardBuffer:
    # --- ClipboardBuffer class remains unchanged ---
    FILENAME = Path(BUFFER_FILENAME); MAX_SIZE = BUFFER_MAX_SIZE
    def __init__(self): self.buffer = self._load()
    def _load(self):
        if self.FILENAME.exists():
            try:
                with self.FILENAME.open('r', encoding='utf-8') as f: content = f.read(); return json.loads(content) if content else []
            except (json.JSONDecodeError, IOError) as e: print(f"Error loading: {e}. Starting empty."); return []
        return []
    def save(self):
        try:
            with self.FILENAME.open('w', encoding='utf-8') as f: json.dump(self.buffer, f, indent=2)
        except IOError as e: print(f"Error saving: {e}")
    def add(self, text):
        if not text or text in self.buffer or len(self.buffer) >= self.MAX_SIZE: return False
        self.buffer.append(text); self.save(); return True
    def remove(self, index):
        if 0 <= index < len(self.buffer): del self.buffer[index]; self.save(); return True
        return False
    def clear(self): self.buffer = []; self.save()
    def is_full(self): return len(self.buffer) >= self.MAX_SIZE
    def __contains__(self, item): return item in self.buffer
    def __len__(self): return len(self.buffer)
    def __getitem__(self, index): return self.buffer[index]

# --- Global Buffer Instance ---
clipboard_buffer = ClipboardBuffer()

# --- UI Action Functions ---
def show_alert(message, style='default'):
    is_error = style == 'error'
    try: console.hud_alert(message, 'error' if is_error else 'success', duration=1.5)
    except Exception: print(f"ALERT ({'Error' if is_error else 'Info'}): {message}")
def import_clipboard():
    text = clipboard.get().strip()
    if not text: show_alert('Clipboard empty or only whitespace', style='error'); return
    if text in clipboard_buffer: show_alert('Item already exists in buffer'); return
    if clipboard_buffer.is_full(): show_alert(f'Buffer full (max {BUFFER_MAX_SIZE} items)', style='error'); return
    if clipboard_buffer.add(text): show_alert('Added clipboard content to buffer')
    else: show_alert('Failed to add clipboard content', style='error')
def clear_all():
    if not clipboard_buffer: show_alert("Buffer is already empty"); return
    try:
        console.alert("Clear Buffer", "Are you sure you want to remove all items?", "Clear All", "Cancel", hide_cancel_button=False)
        count = len(clipboard_buffer); clipboard_buffer.clear()
        show_alert(f"Cleared {count} items from the buffer")
    except KeyboardInterrupt: show_alert("Clear operation cancelled")

# --- View Creation / Presentation Functions ---
def present_clipboard_sheet():
    if not clipboard_buffer: show_alert('Buffer empty'); return
    table_view = ui.TableView()
    def table_tapped(ds):
        if ds.selected_row != -1:
            try: item = ds.items[ds.selected_row]; clipboard.set(item); show_alert('Copied to clipboard'); table_view.close()
            except Exception as e: print(f"Sheet tap/close error: {e}"); show_alert('Error copying or closing', style='error')
    def tableview_cell(tv, section, row):
        cell = ui.TableViewCell('subtitle'); cell.text_label.number_of_lines = 0
        try: item_text = clipboard_buffer[row]; cell.text_label.text = item_text[:150] + ('...' if len(item_text) > 150 else '')
        except IndexError: cell.text_label.text = "Error: Item not found"
        cell.background_color = COLOR_TABLE_CELL_BG; cell.text_label.text_color = COLOR_TABLE_CELL_TEXT
        cell.selected_background_view = ui.View(background_color=COLOR_TABLE_CELL_SELECT_BG)
        return cell
    def tableview_delete(tv, section, row):
        if clipboard_buffer.remove(row): tv.data_source.items = list(clipboard_buffer.buffer); tv.reload_data(); show_alert("Item removed")
        else: show_alert("Error removing item", style='error')
    ds = ui.ListDataSource(list(clipboard_buffer.buffer))
    ds.action = table_tapped; ds.delete_enabled = True
    ds.tableview_cell_for_row = tableview_cell; ds.tableview_delete = tableview_delete
    table_view.data_source = ds; table_view.delegate = ds
    table_view.allows_selection = True
    table_view.present('sheet', hide_title_bar=False)

# --- Custom View Class for Clipboard List (Keyboard Mode) ---
class ClipboardListView(ui.View):
    def __init__(self, back_action=None, close_keyboard_action=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background_color = COLOR_BG_MAIN; self.flex = 'WH'
        self.back_action = back_action; self.close_keyboard_action = close_keyboard_action
        self.table_view = None; self.back_button = None; self.empty_label = None
        self._setup_subviews()
    def _setup_subviews(self):
        self.table_view = ui.TableView()
        ds = ui.ListDataSource(list(clipboard_buffer.buffer))
        ds.action = self._table_tapped_keyboard
        ds.delete_enabled = True
        ds.tableview_cell_for_row = self._tableview_cell; ds.tableview_delete = self._tableview_delete
        self.table_view.data_source = ds; self.table_view.delegate = ds
        self.table_view.allows_selection = True; self.add_subview(self.table_view)
        if self.back_action:
            self.back_button = ui.Button(title=' Menu')
            self.back_button.action = self.back_action; self.back_button.background_color = COLOR_BUTTON_BACK_BG
            self.back_button.tint_color = COLOR_BUTTON_TINT; self.back_button.corner_radius = BUTTON_CORNER_RADIUS / 2
            self.back_button.font = ('<system-bold>', 14); self.back_button.size_to_fit()
            self.back_button.width += 2 * KEYBOARD_MENU_BUTTON_PADDING
            self.back_button.height = KEYBOARD_TOP_BAR_HEIGHT - (2 * KEYBOARD_MENU_BUTTON_PADDING / 2)
            self.add_subview(self.back_button)
        if not clipboard_buffer:
            self.empty_label = ui.Label(text="Buffer Empty", alignment=ui.ALIGN_CENTER, text_color='#AAAAAA')
            self.add_subview(self.empty_label); self.table_view.hidden = True
    def layout(self):
        table_y_offset = 0; top_bar_height = KEYBOARD_TOP_BAR_HEIGHT
        if self.back_button:
            table_y_offset = top_bar_height
            button_y = (top_bar_height - self.back_button.height) / 2
            self.back_button.frame = (KEYBOARD_MENU_BUTTON_PADDING, button_y, self.back_button.width, self.back_button.height)
        if self.table_view: self.table_view.frame = (0, table_y_offset, self.width, self.height - table_y_offset)
        if self.empty_label: self.empty_label.frame = (0, table_y_offset, self.width, self.height - table_y_offset)

    def _table_tapped_keyboard(self, ds):
        """Action when a row is tapped in keyboard mode: Copy and close."""
        if ds.selected_row != -1:
            try:
                # Get item and copy to clipboard
                item = ds.items[ds.selected_row]
                clipboard.set(item)
                show_alert('Copied') # Show confirmation

                # Call close action if provided and callable
                if callable(self.close_keyboard_action):
                    self.close_keyboard_action() # Dismiss the keyboard

            except Exception as e:
                # Handle potential errors during item access, copy, or close
                print(f"Keyboard tap/close error: {e}")
                show_alert('Error copying or closing', style='error')

    def _tableview_cell(self, tv, section, row):
        cell = ui.TableViewCell('subtitle'); cell.text_label.number_of_lines = 0
        try: item_text = clipboard_buffer[row]; cell.text_label.text = item_text[:150] + ('...' if len(item_text) > 150 else '')
        except IndexError: cell.text_label.text = "Error: Item not found"
        cell.background_color = COLOR_TABLE_CELL_BG; cell.text_label.text_color = COLOR_TABLE_CELL_TEXT
        cell.selected_background_view = ui.View(background_color=COLOR_TABLE_CELL_SELECT_BG); return cell
    def _tableview_delete(self, tv, section, row):
        if clipboard_buffer.remove(row):
             self.table_view.data_source.items = list(clipboard_buffer.buffer); self.table_view.reload_data(); show_alert("Removed")
             is_empty = not clipboard_buffer
             if is_empty and not self.empty_label:
                 self.empty_label = ui.Label(text="Buffer Empty", alignment=ui.ALIGN_CENTER, text_color='#AAAAAA')
                 self.add_subview(self.empty_label); self.layout() # Call layout after adding label
             if self.empty_label: self.empty_label.hidden = not is_empty
             self.table_view.hidden = is_empty
        else: show_alert("Error removing", style='error')

# ----------------------------------------

def create_button(title, action, bg_color, is_keyboard_mode=False):
    # Modified to accept a keyboard mode parameter
    button = ui.Button(title=title)
    button.action = lambda sender: action() if callable(action) else None
    button.background_color = bg_color; button.tint_color = COLOR_BUTTON_TINT
    button.corner_radius = BUTTON_CORNER_RADIUS; 
    # Use smaller font for keyboard mode
    button.font = ('<system-bold>', 15 if is_keyboard_mode else 16)
    # Use adaptive sizes for keyboard mode
    button.width = BUTTON_WIDTH
    button.height = KEYBOARD_MODE_BUTTON_HEIGHT if is_keyboard_mode else BUTTON_HEIGHT
    return button

class ClipboardManagerView(ui.View):
    def __init__(self, view_clipboard_action=None, is_keyboard_mode=False, parent_frame=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background_color = COLOR_BG_MAIN
        self._buttons = []; self._view_clipboard_action = view_clipboard_action
        self.is_keyboard_mode = is_keyboard_mode
        self.parent_frame = parent_frame
        self._setup_buttons()
        self.flex = 'WH'  # Make the view flexible in both width and height
        
    def _setup_buttons(self):
        buttons_data = [
            ('Import Clipboard', import_clipboard, COLOR_BUTTON_IMPORT_BG),
            ('View Saved Clipboards', self._view_clipboard_action, COLOR_BUTTON_VIEW_BG),
            ('Clear All', clear_all, COLOR_BUTTON_CLEAR_BG) ]
        for title, action, color in buttons_data:
            if action: 
                button = create_button(title, action, color, self.is_keyboard_mode)
                self.add_subview(button)
                self._buttons.append(button)
    
    def will_close(self):
        """Called before the view is closed"""
        print(f"Menu view will close - current width: {self.width}")
    
    def did_load(self):
        """Called after the view is loaded"""
        print(f"Menu view loaded - current width: {self.width}")
        self.layout()
    
    def layout(self):
        """Position buttons in a vertical column, centered horizontally and vertically."""
        if not self._buttons or self.height <= 0 or self.width <= 0: 
            return
        
        # Debug output to help diagnose sizing issues
        print(f"Layout called - self.width: {self.width}, self.height: {self.height}")
        
        # Use keyboard-specific values when in keyboard mode
        button_height = KEYBOARD_MODE_BUTTON_HEIGHT if self.is_keyboard_mode else BUTTON_HEIGHT
        button_spacing = KEYBOARD_MODE_BUTTON_SPACING if self.is_keyboard_mode else BUTTON_SPACING
        horizontal_padding = 10.0
        
        # Calculate total height needed for all buttons
        num_buttons = len(self._buttons)
        total_button_height = num_buttons * button_height + (num_buttons - 1) * button_spacing
        
        # Calculate the starting y position to center the buttons vertically
        # We calculate the center of the screen, then offset by half the total height of buttons
        start_y = (self.height - total_button_height) / 2.0
        
        # Ensure we don't position buttons off-screen
        start_y = max(10, start_y)
        
        # Calculate button width - set a minimum width to prevent buttons from becoming too narrow
        # This is crucial for when transitioning back from other views
        available_width = self.width - (2 * horizontal_padding)
        button_width = min(BUTTON_WIDTH, available_width)
        button_width = max(KEYBOARD_BUTTON_MIN_WIDTH, button_width)  # Ensure minimum width
        
        # Layout each button
        current_y = start_y
        for button in self._buttons:
            # Center button horizontally
            center_x = self.width / 2.0
            button_x = center_x - (button_width / 2.0)
            
            # Position and size the button
            button.hidden = False
            button.width = button_width
            button.frame = (button_x, current_y, button_width, button_height)
            
            # Move to next button position
            current_y += button_height + button_spacing

# --- Main Execution ---
if __name__ == "__main__":
    console.clear()
    print("Starting Clipboard Buffer Utility...")
    print(f"Buffer loaded with {len(clipboard_buffer)} items.")
    print(f"Using buffer file: {ClipboardBuffer.FILENAME.resolve()}")
    is_keyboard = False
    try: import appex; is_keyboard = appex.is_running_extension()
    except ImportError: pass
    except Exception as e: print(f"Warning: Could not reliably detect execution context: {e}")
    if is_keyboard:
        print("Running as Keyboard Extension")
        keyboard_root_view = ui.View(background_color=COLOR_BG_MAIN)
        keyboard_root_view.flex = 'WH'
        view_state = { 'main_menu': None, 'clipboard_list': None, 'active_view': None }
        
        def remove_active_view():
            """Remove the currently active view from the keyboard root view."""
            if view_state['active_view'] and view_state['active_view'].superview:
                keyboard_root_view.remove_subview(view_state['active_view'])
            view_state['active_view'] = None
        
        def close_keyboard():
            """Close the keyboard entirely."""
            print("Closing keyboard...")
            keyboard_root_view.close()
        
        def show_main_menu(sender=None):
            """Show the main menu view, creating it if necessary."""
            print(f"Switching to Main Menu view - root width: {keyboard_root_view.width}")
            
            # Remove the current active view if there is one
            remove_active_view()
            
            # Create the main menu if it doesn't exist, or reset its frame if it does
            if not view_state['main_menu']:
                view_state['main_menu'] = ClipboardManagerView(
                    view_clipboard_action=show_clipboard_list,
                    is_keyboard_mode=True,
                    parent_frame=keyboard_root_view.frame
                )
            
            # Set the frame of the menu view to match the root view before adding it
            # This ensures the menu takes up the full available space
            view_state['main_menu'].frame = (0, 0, keyboard_root_view.width, keyboard_root_view.height)
            keyboard_root_view.add_subview(view_state['main_menu'])
            view_state['active_view'] = view_state['main_menu']
            
            # Force a layout update
            view_state['main_menu'].layout()
        
        def show_clipboard_list(sender=None):
            """Show the clipboard list view."""
            print(f"Switching to Clipboard List view - root width: {keyboard_root_view.width}")
            
            # Remove the current active view
            remove_active_view()
            
            # Create a new clipboard list view
            view_state['clipboard_list'] = ClipboardListView(
                back_action=show_main_menu,
                close_keyboard_action=close_keyboard
            )
            
            # Set the frame of the list view to match the root view before adding it
            view_state['clipboard_list'].frame = (0, 0, keyboard_root_view.width, keyboard_root_view.height)
            keyboard_root_view.add_subview(view_state['clipboard_list'])
            view_state['active_view'] = view_state['clipboard_list']
        
        # Start with the clipboard list view
        show_clipboard_list()
        
        # Present the keyboard view
        keyboard_root_view.present('keyboard')
    else:
        print("Running as Main App / Sheet")
        main_view_app = ClipboardManagerView(view_clipboard_action=present_clipboard_sheet)
        main_view_app.present('sheet', hide_title_bar=True)
