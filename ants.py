import ui
import json
import os
from datetime import datetime, timedelta

FILENAME = 'ants.json'
DATESTR = '%m-%d-%Y %H:%M:%S'

class CustomAlert(ui.View):
    def __init__(self, save_callback):
        self.setup_view()
        self.save_callback = save_callback
        self.add_labels_and_buttons()

    def setup_view(self):
        self.background_color = 'white'
        self.border_color = 'black'
        self.border_width = 1
        self.corner_radius = 5
        self.frame = (0, 0, 300, 120)
        self.name = 'Update Timestamp?'

    def add_labels_and_buttons(self):
        title_label = ui.Label(frame=(0, 0, 300, 40), text=self.name, alignment=ui.ALIGN_CENTER)
        self.add_subview(title_label)

        update_btn = NotesApp.create_button((30, 70, 100, 40), 'Update', 'red', self.update_action)
        self.add_subview(update_btn)

        keep_btn = NotesApp.create_button((170, 70, 100, 40), 'Keep', 'blue', self.keep_action)
        self.add_subview(keep_btn)

    def update_action(self, sender):
        self.save_callback(True)
        self.close_alert()

    def keep_action(self, sender):
        self.save_callback(False)
        self.close_alert()

    def close_alert(self):
        self.superview.remove_subview(self)

class TextViewDelegate:
    def __init__(self, change_action):
        self.change_action = change_action

    def textview_did_change(self, textview):
        self.change_action(textview)

class NotesApp(ui.View):
    def __init__(self):
        self.load_notes()
        self.updating_comment_index = None
        self.is_comment_search_active = False
        self.create_ui_elements()

    def create_ui_elements(self):
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
        w, h = self.width, self.height
        if w > h:  # Landscape
            # Adjust frames for landscape orientation
            # Only adjust the notes_list to be on the right
            self.notes_list.frame = (w // 2, 10, w // 2 - 10, h - 20)
        else:  # Portrait
            # Restore original frame for portrait orientation
            self.notes_list.frame = (10, 335, 370, 385)
        self.filter_notes(None)

    def input_change(self, sender):
        if sender == self.id_input:
                # If Enter key is pressed and the ID input is not empty, filter notes by ID
                self.filter_notes(None)
        elif sender == self.comment_input:
            id_text = self.id_input.text.strip()
            comment_text = self.comment_input.text.strip()
            if id_text or comment_text:
                action = self.save_note if id_text and comment_text else self.filter_notes
                self.update_dynamic_button('Save' if id_text and comment_text else 'Search', action)

    def setup_ui_properties(self):
        self.name = 'Advanced Note Taking System'
        self.background_color = 'white'

    def add_identifier_input(self):
        self.id_input = ui.TextField(frame=(10, 10, 370, 32), placeholder='Unique identifier (Asset number)', continuous=True)
        self.id_input.font = ('<system-bold>', 20)
        self.id_input.alignment = ui.ALIGN_CENTER
        self.add_subview(self.id_input)

    def add_comment_label(self):
        self.comment_label = ui.Label(frame=(10, 55, 370, 20), text="Comment:")
        self.add_subview(self.comment_label)

    def add_comment_input(self):
        self.comment_input = ui.TextView(frame=(10, 85, 370, 120), border_width=1, corner_radius=8)
        self.comment_input.font = ('<system>', 17)
        self.add_subview(self.comment_input)

    def add_dynamic_button(self):
        self.dynamic_button = self.create_button((70, 225, 100, 40), 'Search', 'blue', self.filter_notes)
        self.add_subview(self.dynamic_button)

    def update_dynamic_button(self, title, action):
        self.dynamic_button.title = title
        self.dynamic_button.action = action

    def add_clear_button(self):
        self.clear_button = self.create_button((220, 225, 100, 40), 'Clear', 'red', self.clear_input)
        self.add_subview(self.clear_button)

    def add_timeframe_control(self):
        self.timeframe_control = ui.SegmentedControl(frame=(10, 280, 370, 32), segments=['All', 'Day', 'Week', 'Month'])
        self.timeframe_control.selected_index = 0
        self.add_subview(self.timeframe_control)

    def add_notes_list(self):
        self.notes_list = ui.TableView(frame=(10, 335, 370, 385))
        self.notes_list.data_source = self
        self.notes_list.delegate = self
        self.add_subview(self.notes_list)

    @staticmethod
    def create_button(frame, title, bg_color, action):
        btn = ui.Button(frame=frame, type='custom')
        btn.title = title
        btn.background_color = bg_color
        btn.tint_color = 'white'
        btn.corner_radius = 10
        btn.action = action
        return btn

    def get_timeframe_delta(self):
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
        return sorted(
            comments,
            key=lambda x: datetime.strptime(x.split(": ", 1)[0], DATESTR),
            reverse=True
        )

    def get_relevant_comments(self, comments, delta=None, query=None):
        now = datetime.now()
        filtered_comments = comments

        if delta is not None:
            filtered_comments = [comment for comment in filtered_comments if now - datetime.strptime(comment.split(": ", 1)[0], DATESTR) <= delta]

        if query and self.is_comment_search_active:
            filtered_comments = [comment for comment in filtered_comments if query in comment.lower()]

        return self.sort_comments(filtered_comments)

    def filter_notes(self, sender):
        current_id = self.id_input.text.lower().strip()
        comment_query = self.comment_input.text.lower().strip()
        delta = self.get_timeframe_delta()

        self.displayed_notes = {}
        for key, comments in self.original_notes.items():
            if (not current_id or key.lower().startswith(current_id)):
                filtered_comments = self.get_relevant_comments(comments, delta, comment_query)
                if filtered_comments:
                    self.displayed_notes[key] = filtered_comments

        if current_id:
            self.displayed_notes.setdefault(current_id, [])

        self.update_notes_list()
        ui.end_editing()

        # Update the flag based on whether the comment input is the only field with text
        self.is_comment_search_active = bool(comment_query and not current_id)

    def update_notes_list(self):
        if self.displayed_notes and self.id_input.text in self.displayed_notes:
            self.notes_list.data_source.comments = self.displayed_notes[self.id_input.text]
        elif hasattr(self.notes_list.data_source, 'comments'):
            delattr(self.notes_list.data_source, 'comments')
        self.notes_list.reload()

    def load_notes(self):
        if os.path.exists(FILENAME):
            with open(FILENAME, 'r') as f:
                self.notes = json.load(f)
        else:
            self.notes = {}
        self.original_notes = dict(self.notes)
        self.displayed_notes = dict(self.notes)

    def save_notes_to_file(self):
        with open(FILENAME, 'w') as f:
            json.dump(self.notes, f)
        self.load_notes()
        self.notes_list.reload()

    def clear_input(self, sender):
        if self.comment_input.text:
            self.clear_comment_input()
        elif self.id_input.text:
            self.clear_id_input()
        self.filter_notes(None)
        self.update_dynamic_button('Search', self.filter_notes)
        ui.end_editing()

    def clear_comment_input(self):
        self.comment_input.text = ''
        self.updating_comment_index = None
        self.notes_list.selected_row = -1
        if self.is_comment_search_active:
            self.id_input.text = ''
            self.is_comment_search_active = False

    def clear_id_input(self):
        self.id_input.text = ''
        self.displayed_notes = dict(self.original_notes)
        if hasattr(self.notes_list.data_source, 'comments'):
            delattr(self.notes_list.data_source, 'comments')

    def save_note(self, sender):
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
        def save_callback(update_timestamp):
            self.perform_save(self.id_input.text.strip(), self.comment_input.text.strip(), update_timestamp)
            self.input_change(None)

        alert_view = CustomAlert(save_callback)
        alert_view.center = (self.width * 0.5, self.height * 0.5)
        self.add_subview(alert_view)

    def perform_save(self, identifier, comment, update_timestamp):
        comment_with_timestamp = f"{datetime.now().strftime(DATESTR)}: {comment}" if update_timestamp else f"{self.notes[identifier][self.updating_comment_index].split(': ', 1)[0]}: {comment}"

        if self.updating_comment_index is not None:
            self.notes[identifier][self.updating_comment_index] = comment_with_timestamp
            self.updating_comment_index = None
        else:
            self.notes.setdefault(identifier, []).append(comment_with_timestamp)

        self.comment_input.text = ''
        self.refresh_comments_list(identifier)
        self.filter_notes(None)
        ui.end_editing()

    def refresh_comments_list(self, identifier):
        if hasattr(self.notes_list.data_source, 'comments'):
            sorted_comments = self.get_relevant_comments(self.notes[identifier])
            self.notes_list.data_source.comments = sorted_comments
            self.notes_list.reload()

        self.save_notes_to_file()

    def delete_entry(self, identifier=None, comment_index=None):
        if comment_index is not None:
            del self.notes[identifier][comment_index]
            if not self.notes[identifier]:
                del self.notes[identifier]
        elif identifier:
            del self.notes[identifier]
        self.save_notes_to_file()

    def tableview_did_select(self, tableview, section, row):
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
        return True

    def delete_comment(self, identifier, comment_index):
        del self.notes[identifier][comment_index]
        if not self.notes[identifier]:  # If no comments left, remove the identifier too
            del self.notes[identifier]

    def delete_identifier(self, identifier):
        del self.notes[identifier]

    def tableview_delete(self, tableview, section, row):
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
        return text[:length] + '...' if len(text) > length else text

    def tableview_number_of_sections(self, tableview):
        if self.comment_input.text.strip():
            return len(self.displayed_notes)  # Each matching ID for a comment search gets a section
        return 1  # Default single section for normal ID display or specific ID match

    def tableview_number_of_rows(self, tableview, section):
        if self.comment_input.text.strip():
            identifier = list(self.displayed_notes.keys())[section]
            return len(self.displayed_notes[identifier])
        elif self.id_input.text.strip() and self.id_input.text.strip() in self.displayed_notes:
            # If there's an exact match ID, display all its comments
            identifier = self.id_input.text.strip()
            return len(self.displayed_notes[identifier])
        return len(self.displayed_notes)  # Default behavior, showing all IDs

    def tableview_title_for_header(self, tableview, section):
        if self.is_comment_search_active:
            # When searching by comment, display the actual identifier as section header
            identifier = list(self.displayed_notes.keys())[section]
            return identifier
        elif hasattr(tableview.data_source, 'comments'):
            # When an ID has been selected and is displaying comments
            num_comments = len(tableview.data_source.comments)
            return f'Comments ({num_comments})'
        # Default case when neither specific comment search nor ID-based comment display is active
        return 'Identifiers'

    def format_comment(self, comment, query):
        """Highlights the query in the comment and truncates surrounding text."""
        max_length = 100
        query = query.lower()
        lower_comment = comment.lower()
        query_start = lower_comment.find(query)
        
        if query_start == -1:
            return comment if len(comment) <= max_length else comment[:max_length] + '...'
        
        # Ensure the query is centered in the output
        start = max(query_start + len(query) // 2 - max_length // 2, 0)
        start = min(start, query_start)
        end = min(start + max_length, len(comment))

        formatted_comment = comment[start:end]
        if start > 0:
            formatted_comment = '...' + formatted_comment
        if end < len(comment):
            formatted_comment += '...'

        # Highlight the query in the formatted comment
        query_start_in_formatted = formatted_comment.lower().find(query)
        highlighted_comment = (formatted_comment[:query_start_in_formatted] +
                            "[" + formatted_comment[query_start_in_formatted:query_start_in_formatted + len(query)] + "]" +
                            formatted_comment[query_start_in_formatted + len(query):])

        return highlighted_comment

    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell('subtitle')
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
        return cell

    def extract_comment_data(self, comment_data):
        timestamp, comment = comment_data.split(": ", 1)
        return timestamp, comment

    def extract_identifier_data(self, identifier):
        if self.comment_input.text.strip():
            # Only consider comments that contain the search text
            relevant_comments = [comment for comment in self.displayed_notes[identifier] if self.comment_input.text.lower().strip() in comment.lower()]
        else:
            # Consider all comments for this identifier
            relevant_comments = self.displayed_notes.get(identifier, [])

        comment_count = len(relevant_comments)
        most_recent_date = relevant_comments[0].split(": ", 1)[0].split(" ")[0] if relevant_comments else "No date"
        return comment_count, most_recent_date

if __name__ == '__main__':
    app = NotesApp()
    app.present('full_screen')