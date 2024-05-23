import ui
import json
import os
from datetime import datetime, timedelta

FILENAME = 'ants.json'
DATESTR = '%m-%d-%Y %H:%M:%S'

class NotesApp(ui.View):
    @staticmethod
    def create_button(frame, title, bg_color, action):
        # Create a button with specified properties
        btn = ui.Button(frame=frame, type='custom')
        btn.title = title
        btn.background_color = bg_color
        btn.tint_color = 'white'
        btn.corner_radius = 10
        btn.action = action
        return btn

    def __init__(self):
        # Initialize the app, load notes, and set up UI elements
        self.load_notes()
        self.updating_comment_index = None
        self.is_comment_search_active = False
        self.create_ui_elements()
        self.filter_notes(None)

    def create_ui_elements(self):
        # Create and add all UI elements to the view
        self.setup_ui_properties()
        self.add_identifier_input()
        self.add_comment_label()
        self.add_comment_input()
        self.add_dynamic_button()
        self.add_clear_button()
        self.add_timeframe_control()
        self.add_notes_list()
        self.id_input.action = self.input_change
        self.comment_input.delegate = TextViewDelegate(self.input_change)
        self.timeframe_control.action = self.filter_notes

    def layout(self):
        # Adjust layout based on orientation
        w, h = self.width, self.height
        if w > h:  # Landscape
            self.notes_list.frame = (w // 2, 10, w // 2 - 10, h - 20)
        else:  # Portrait
            self.notes_list.frame = (10, 335, 370, 385)

    def setup_ui_properties(self):
        # Set basic properties for the main view
        self.name = 'Advanced Note Taking System'
        self.background_color = 'white'

    def add_identifier_input(self):
        # Add text field for unique identifier input
        self.id_input = ui.TextField(frame=(10, 10, 370, 32), placeholder='Unique identifier (Asset number)', continuous=True)
        self.id_input.font = ('<system-bold>', 20)
        self.id_input.alignment = ui.ALIGN_CENTER
        self.add_subview(self.id_input)

    def add_comment_label(self):
        # Add label for the comment input field
        self.comment_label = ui.Label(frame=(10, 55, 370, 20), text="Comment:")
        self.add_subview(self.comment_label)

    def add_comment_input(self):
        # Add text view for comment input
        self.comment_input = ui.TextView(frame=(10, 85, 370, 120), border_width=1, corner_radius=8)
        self.comment_input.font = ('<system>', 17)
        self.add_subview(self.comment_input)

    def add_dynamic_button(self):
        # Add dynamic button for search/save actions
        self.dynamic_button = self.create_button((70, 225, 100, 40), 'Search', 'blue', self.filter_notes)
        self.add_subview(self.dynamic_button)

    def update_dynamic_button(self, title, action):
        # Update the dynamic button's title and action
        self.dynamic_button.title = title
        self.dynamic_button.action = action

    def add_clear_button(self):
        # Add button to clear input fields
        self.clear_button = self.create_button((220, 225, 100, 40), 'Clear', 'red', self.clear_input)
        self.add_subview(self.clear_button)

    def add_timeframe_control(self):
        # Add segmented control for timeframe filtering
        self.timeframe_control = ui.SegmentedControl(frame=(10, 280, 370, 32), segments=['All', 'Day', 'Week', 'Month'])
        self.timeframe_control.selected_index = 0
        self.add_subview(self.timeframe_control)

    def add_notes_list(self):
        # Add table view to display notes
        self.notes_list = ui.TableView(frame=(10, 335, 370, 385))
        self.notes_list.data_source = self
        self.notes_list.delegate = self
        self.add_subview(self.notes_list)

    def input_change(self, sender):
        # Handle input changes and update UI elements accordingly
        if sender == self.id_input:
            self.filter_notes(None)
        elif sender == self.comment_input:
            id_text = self.id_input.text.strip()
            comment_text = self.comment_input.text.strip()
            if id_text or comment_text:
                action = self.save_note if id_text and comment_text else self.filter_notes
                self.update_dynamic_button('Save' if id_text and comment_text else 'Search', action)

    def get_timeframe_delta(self):
        # Determine the time delta based on the selected timeframe
        timeframe = self.timeframe_control.selected_index
        delta = None
        if timeframe == 1:
            delta = timedelta(days=1)
        elif timeframe == 2:
            delta = timedelta(weeks=1)
        elif timeframe == 3:
            delta = timedelta(days=30)
        return delta

    def sort_comments(self, comments):
        # Sort comments by date in descending order
        return sorted(
            comments,
            key=lambda x: datetime.strptime(x.split(": ", 1)[0], DATESTR),
            reverse=True
        )

    def get_relevant_comments(self, comments, delta=None, query=None):
        # Filter comments based on the timeframe and search query
        now = datetime.now()
        filtered_comments = comments

        if delta is not None:
            filtered_comments = [comment for comment in filtered_comments if now - datetime.strptime(comment.split(": ", 1)[0], DATESTR) <= delta]

        if query and self.is_comment_search_active:
            filtered_comments = [comment for comment in filtered_comments if query in comment.lower()]

        return self.sort_comments(filtered_comments)

    def filter_notes(self, sender):
        # Filter notes based on the input identifier and comments
        current_id = self.id_input.text.lower().strip()
        comment_query = self.comment_input.text.lower().strip()

        self.is_comment_search_active = bool(comment_query and not current_id)

        delta = self.get_timeframe_delta()

        self.displayed_notes = {}
        for key, comments in self.original_notes.items():
            if not current_id or key.lower().startswith(current_id):
                filtered_comments = self.get_relevant_comments(comments, delta, comment_query)
                if filtered_comments:
                    self.displayed_notes[key] = filtered_comments

        if current_id and current_id in self.original_notes:
            self.displayed_notes.setdefault(current_id, [])

        self.update_notes_list()
        ui.end_editing()

    def update_notes_list(self):
        # Update the table view to display filtered notes
        if self.displayed_notes and self.id_input.text in self.displayed_notes:
            self.notes_list.data_source.comments = self.displayed_notes[self.id_input.text]
        elif hasattr(self.notes_list.data_source, 'comments'):
            delattr(self.notes_list.data_source, 'comments')
        self.notes_list.reload()

    def load_notes(self):
        # Load notes from a JSON file
        if os.path.exists(FILENAME):
            with open(FILENAME, 'r') as f:
                self.notes = json.load(f)
        else:
            self.notes = {}
        self.original_notes = dict(self.notes)
        self.displayed_notes = dict(self.notes)

    def save_notes_to_file(self):
        # Save notes to a JSON file
        with open(FILENAME, 'w') as f:
            json.dump(self.notes, f)
        self.load_notes()
        self.notes_list.reload()

    def clear_input(self, sender):
        # Clear input fields based on their current state
        if self.comment_input.text:
            self.clear_comment_input()
        elif self.id_input.text:
            self.clear_id_input()
        self.filter_notes(None)
        self.update_dynamic_button('Search', self.filter_notes)
        ui.end_editing()

    def clear_comment_input(self):
        # Clear the comment input field
        self.comment_input.text = ''
        self.updating_comment_index = None
        self.notes_list.selected_row = -1
        if self.is_comment_search_active:
            self.id_input.text = ''
            self.is_comment_search_active = False

    def clear_id_input(self):
        # Clear the ID input field
        self.id_input.text = ''
        self.displayed_notes = dict(self.original_notes)
        if hasattr(self.notes_list.data_source, 'comments'):
            delattr(self.notes_list.data_source, 'comments')

    def save_note(self, sender):
        # Save a new note or update an existing one
        identifier = self.id_input.text.strip()
        comment = self.comment_input.text.strip()

        if not (identifier and comment):
            return

        ui.end_editing()

        if self.updating_comment_index is not None:
            self.show_custom_alert()
        else:
            self.perform_save(identifier, comment, True)

    def show_custom_alert(self):
        # Show an alert to confirm if the timestamp should be updated
        def save_callback(update_timestamp):
            self.perform_save(self.id_input.text.strip(), self.comment_input.text.strip(), update_timestamp)
            self.input_change(None)

        alert_view = CustomAlert(save_callback)
        alert_view.center = (self.width * 0.5, self.height * 0.5)
        self.add_subview(alert_view)

    def perform_save(self, identifier, comment, update_timestamp):
        # Perform the save operation for a note
        comment_with_timestamp = f"{datetime.now().strftime(DATESTR)}: {comment}" if update_timestamp else f"{self.notes[identifier][self.updating_comment_index].split(': ', 1)[0]}: {comment}"

        if self.updating_comment_index is not None:
            self.notes[identifier][self.updating_comment_index] = comment_with_timestamp
            self.updating_comment_index = None
        else:
            self.notes.setdefault(identifier, []).append(comment_with_timestamp)

        self.comment_input.text = ''
        self.refresh_comments_list(identifier)
        self.save_notes_to_file()
        self.filter_notes(None)
        ui.end_editing()

    def refresh_comments_list(self, identifier):
        # Refresh the comments list for a specific identifier
        if hasattr(self.notes_list.data_source, 'comments'):
            sorted_comments = self.get_relevant_comments(self.notes[identifier])
            self.notes_list.data_source.comments = sorted_comments
            self.notes_list.reload()

    def delete_entry(self, identifier=None, comment_index=None):
        # Delete a specific comment or an entire identifier
        if comment_index is not None:
            del self.notes[identifier][comment_index]
            if not self.notes[identifier]:
                del self.notes[identifier]
        elif identifier:
            del self.notes[identifier]
        self.save_notes_to_file()

    def tableview_did_select(self, tableview, section, row):
        # Handle table view row selection
        if self.is_comment_search_active:
            identifier = list(self.displayed_notes.keys())[section]
            self.id_input.text = identifier
            selected_comment = self.displayed_notes[identifier][row]
            self.comment_input.text = selected_comment.split(": ", 1)[1]
            self.updating_comment_index = self.notes[identifier].index(selected_comment)
        else:
            if hasattr(tableview.data_source, 'comments'):
                selected_comment = tableview.data_source.comments[row]
                self.updating_comment_index = self.notes[self.id_input.text].index(selected_comment)
                self.comment_input.text = selected_comment.split(": ", 1)[1]
            else:
                identifier = sorted(self.displayed_notes.keys())[row]
                self.id_input.text = identifier
                now = datetime.now()
                delta = self.get_timeframe_delta()
                relevant_comments = self.displayed_notes[identifier]
                self.notes_list.data_source = self
                self.notes_list.data_source.comments = relevant_comments
                self.notes_list.reload()
        self.input_change(self.comment_input)

    def tableview_can_delete(self, tableview, section, row):
        # Allow table view rows to be deleted
        return True

    def delete_comment(self, identifier, comment_index):
        # Delete a specific comment for an identifier
        del self.notes[identifier][comment_index]
        if not self.notes[identifier]:  # If no comments left, remove the identifier too
            del self.notes[identifier]

    def delete_identifier(self, identifier):
        # Delete an entire identifier and its comments
        del self.notes[identifier]

    def tableview_delete(self, tableview, section, row):
        # Handle deletion of a row in the table view
        if hasattr(tableview.data_source, 'comments'):
            comment_to_delete = tableview.data_source.comments[row]
            self.delete_comment(self.id_input.text, self.notes[self.id_input.text].index(comment_to_delete))
        else:
            identifier = sorted(self.displayed_notes.keys())[row]
            self.delete_identifier(identifier)
        self.save_notes_to_file()
        self.filter_notes(None)
        tableview.reload()

    def truncate_text(self, text, length):
        # Truncate text to a specific length with ellipsis
        return text[:length] + '...' if len(text) > length else text

    def tableview_number_of_sections(self, tableview):
        # Determine the number of sections in the table view
        if self.is_comment_search_active:
            return max(1, len(self.displayed_notes))
        return 1  # Default to one section for normal ID display or specific ID match

    def tableview_number_of_rows(self, tableview, section):
        # Determine the number of rows in each section of the table view
        if self.is_comment_search_active:
            if not self.displayed_notes:
                return 0
            identifiers = list(self.displayed_notes.keys())
            comments_for_section = self.displayed_notes.get(identifiers[section], [])
            return len(comments_for_section)

        current_id_input = self.id_input.text.strip().lower()
        if current_id_input:
            exact_match_comments = self.displayed_notes.get(current_id_input)
            if exact_match_comments is not None:
                return len(exact_match_comments) - 1 if not exact_match_comments else len(exact_match_comments)
            matching_ids = [key for key in self.displayed_notes.keys() if key.lower().startswith(current_id_input)]
            return len(matching_ids)

        return len(self.displayed_notes)

    def tableview_title_for_header(self, tableview, section):
        # Determine the title for each section header in the table view
        if self.is_comment_search_active:
            if not any(self.displayed_notes.values()):
                return "No results..."
            return list(self.displayed_notes.keys())[section]  # Displays the matched identifier as header

        if hasattr(tableview.data_source, 'comments'):
            return f'Comments ({len(tableview.data_source.comments)})'

        if not self.displayed_notes:
            return 'No identifiers...'

        return 'Identifiers'  # Default header for non-search scenarios

    def format_comment(self, comment, query):
        # Highlight the query in the comment and truncate surrounding text
        max_length = 100
        query = query.lower()
        lower_comment = comment.lower()
        query_start = lower_comment.find(query)

        if query_start == -1:
            return comment if len(comment) <= max_length else comment[:max_length] + '...'

        start = max(query_start + len(query) // 2 - max_length // 2, 0)
        start = min(start, query_start)
        end = min(start + max_length, len(comment))

        formatted_comment = comment[start:end]
        if start > 0:
            formatted_comment = '...' + formatted_comment
        if end < len(comment):
            formatted_comment += '...'

        query_start_in_formatted = formatted_comment.lower().find(query)
        highlighted_comment = (formatted_comment[:query_start_in_formatted] +
                            "[" + formatted_comment[query_start_in_formatted:query_start_in_formatted + len(query)] + "]" +
                            formatted_comment[query_start_in_formatted + len(query):])

        return highlighted_comment

    def tableview_cell_for_row(self, tableview, section, row):
        # Create and configure table view cells
        cell = ui.TableViewCell('subtitle')
        try:
            if self.is_comment_search_active:
                identifier = list(self.displayed_notes.keys())[section]
                timestamp, comment = self.extract_comment_data(self.displayed_notes[identifier][row])
                cell.text_label.text = timestamp
                cell.detail_text_label.text = self.format_comment(comment, self.comment_input.text.strip())
            elif self.id_input.text.strip() in self.displayed_notes:
                identifier = self.id_input.text.strip()
                timestamp, comment = self.extract_comment_data(self.displayed_notes[identifier][row])
                cell.text_label.text = timestamp
                cell.detail_text_label.text = self.truncate_text(comment, 100)
            else:
                identifier = sorted(self.displayed_notes.keys())[row]
                comment_count, most_recent_date = self.extract_identifier_data(identifier)
                comment_text = "comment" if comment_count == 1 else "comments"
                cell.text_label.text = identifier
                cell.detail_text_label.text = f"{comment_count} {comment_text} | {most_recent_date}"
        except IndexError:
            return None
        return cell

    def extract_comment_data(self, comment_data):
        # Extract timestamp and comment from a comment string
        timestamp, comment = comment_data.split(": ", 1)
        return timestamp, comment

    def extract_identifier_data(self, identifier):
        # Extract comment count and most recent date for an identifier
        if self.comment_input.text.strip():
            relevant_comments = [comment for comment in self.displayed_notes[identifier] if self.comment_input.text.lower().strip() in comment.lower()]
        else:
            relevant_comments = self.displayed_notes.get(identifier, [])

        comment_count = len(relevant_comments)
        most_recent_date = relevant_comments[0].split(": ", 1)[0].split(" ")[0] if relevant_comments else "No date"
        return comment_count, most_recent_date

class CustomAlert(ui.View):
    def __init__(self, save_callback):
        # Initialize the custom alert view
        self.setup_view()
        self.save_callback = save_callback
        self.add_labels_and_buttons()

    def setup_view(self):
        # Set up the custom alert view properties
        self.background_color = 'white'
        self.border_color = 'black'
        self.border_width = 1
        self.corner_radius = 5
        self.frame = (0, 0, 300, 120)
        self.name = 'Update Timestamp?'

    def add_labels_and_buttons(self):
        # Add labels and buttons to the custom alert view
        title_label = ui.Label(frame=(0, 0, 300, 40), text=self.name, alignment=ui.ALIGN_CENTER)
        self.add_subview(title_label)

        update_btn = NotesApp.create_button((30, 70, 100, 40), 'Update', 'red', self.update_action)
        self.add_subview(update_btn)

        keep_btn = NotesApp.create_button((170, 70, 100, 40), 'Keep', 'blue', self.keep_action)
        self.add_subview(keep_btn)

    def update_action(self, sender):
        # Action for the "Update" button
        self.save_callback(True)
        self.close_alert()

    def keep_action(self, sender):
        # Action for the "Keep" button
        self.save_callback(False)
        self.close_alert()

    def close_alert(self):
        # Close the custom alert view
        self.superview.remove_subview(self)

class TextViewDelegate:
    def __init__(self, change_action):
        # Initialize the text view delegate
        self.change_action = change_action

    def textview_did_change(self, textview):
        # Handle text view changes
        self.change_action(textview)

if __name__ == '__main__':
    app = NotesApp()
    app.present('full_screen')
