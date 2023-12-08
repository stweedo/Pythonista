import ui
import json
import os
from datetime import datetime, timedelta

FILENAME = 'ants.json'
DATESTR = '%m-%d-%Y %H:%M:%S'

class NotesApp(ui.View):
    def __init__(self):
        self.load_notes()
        self.updating_comment_index = None
        self.create_ui_elements()

    def create_ui_elements(self):
        self.setup_ui_properties()
        self.add_identifier_input()
        self.add_comment_label()
        self.add_comment_input()
        self.add_save_button()
        self.add_clear_button()
        self.add_timeframe_control()
        self.add_notes_list()
        self.id_input.action = self.filter_notes
        self.timeframe_control.action = self.filter_notes

    def setup_ui_properties(self):
        self.name = 'Advanced Note Taking System'
        self.background_color = 'white'

    def add_identifier_input(self):
        self.id_input = ui.TextField(frame=(10, 10, 370, 32), placeholder='Unique identifier (e.g., Asset number)', continuous=True)
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

    def add_save_button(self):
        self.save_button = self.create_button((70, 225, 100, 40), 'Save', 'blue', self.save_note)
        self.add_subview(self.save_button)

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

    def create_button(self, frame, title, bg_color, action):
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
    
    def get_relevant_comments(self, comments, delta):
        now = datetime.now()
        return [comment for comment in comments if not delta or now - datetime.strptime(comment.split(": ", 1)[0], DATESTR) <= delta]
    
    def get_sorted_comments(self, identifier):
        return sorted(
            self.notes[identifier], 
            key=lambda x: datetime.strptime(x.split(": ", 1)[0], DATESTR), 
            reverse=True
        )

    def filter_notes(self, sender):
        """Filters notes based on the current identifier and timeframe."""
        current_identifier = self.id_input.text.lower()
        delta = self.get_timeframe_delta()
        self.displayed_notes = {
            key: self.get_relevant_comments(value, delta)
            for key, value in self.original_notes.items()
            if not current_identifier or key.lower().startswith(current_identifier)
        }
        # Remove entries with no relevant comments
        self.displayed_notes = {k: v for k, v in self.displayed_notes.items() if v}
        self.refresh_notes_list()

    def refresh_notes_list(self):
        """Refreshes the notes list view with currently displayed notes."""
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
            self.comment_input.text = ''
            self.updating_comment_index = None
            self.notes_list.selected_row = -1
        elif self.id_input.text:
            self.id_input.text = ''
            self.displayed_notes = dict(self.original_notes)
            if hasattr(self.notes_list.data_source, 'comments'):
                delattr(self.notes_list.data_source, 'comments')
            self.filter_notes(None)
        ui.end_editing()

    def save_note(self, sender):
        identifier = self.id_input.text.strip()
        comment = self.comment_input.text.strip()
        
        if not (identifier and comment):
            return
        
        comment_with_timestamp = f"{datetime.now().strftime(DATESTR)}: {comment}"
        
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
            sorted_comments = self.get_sorted_comments(identifier)
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
      if hasattr(tableview.data_source, 'comments'):
          selected_comment = tableview.data_source.comments[row]
          self.updating_comment_index = self.notes[self.id_input.text].index(selected_comment)
          self.comment_input.text = selected_comment.split(": ", 1)[1]
      else:
          identifier = sorted(self.displayed_notes.keys())[row]
          self.id_input.text = identifier
          
          now = datetime.now()
          delta = self.get_timeframe_delta()
          
          sorted_comments = self.get_sorted_comments(identifier)
          relevant_comments = self.get_relevant_comments(sorted_comments, delta)
          
          self.notes_list.data_source = self
          self.notes_list.data_source.comments = relevant_comments
          self.notes_list.reload()

    def tableview_number_of_rows(self, tableview, section):
        if hasattr(tableview.data_source, 'comments'):
            return len(tableview.data_source.comments)
        return len(self.displayed_notes)

    def tableview_can_delete(self, tableview, section, row):
        return True

    def tableview_delete(self, tableview, section, row):
        if hasattr(tableview.data_source, 'comments'):
            comment_to_delete = tableview.data_source.comments[row]
            self.notes[self.id_input.text].remove(comment_to_delete)
            if not self.notes[self.id_input.text]:
                del self.notes[self.id_input.text]
                if hasattr(self.notes_list.data_source, 'comments'):
                    delattr(self.notes_list.data_source, 'comments')
            else:
                self.notes_list.data_source.comments = sorted(self.notes[self.id_input.text], 
                                                              key=lambda x: datetime.strptime(x.split(": ", 1)[0], DATESTR), 
                                                              reverse=True)
            self.save_notes_to_file()
            self.filter_notes(None)
            tableview.reload()
        else:
            identifier = sorted(self.displayed_notes.keys())[row]
            self.delete_entry(identifier=identifier)
            self.original_notes = dict(self.notes)
            self.filter_notes(None)
            tableview.reload()

    @staticmethod
    def truncate_text(text, length):
        return text[:length] + '...' if len(text) > length else text

    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell('subtitle')
        if hasattr(tableview.data_source, 'comments'):
            comment_data = tableview.data_source.comments[row]
            timestamp, comment = self.extract_comment_data(comment_data)
            cell.text_label.text = timestamp
            cell.detail_text_label.text = self.truncate_text(comment, 60)
        else:
            identifier = sorted(self.displayed_notes.keys())[row]
            comment_count, most_recent_date = self.extract_identifier_data(identifier)
            cell.text_label.text = identifier
            cell.detail_text_label.text = f"{comment_count} comment{'s' if comment_count != 1 else ''} | {most_recent_date}"

        return cell

    def extract_comment_data(self, comment_data):
        timestamp, comment = comment_data.split(": ", 1)
        return timestamp, comment

    def extract_identifier_data(self, identifier):
        now = datetime.now()
        delta = self.get_timeframe_delta()

        sorted_comments = self.get_sorted_comments(identifier)
        relevant_comments = self.get_relevant_comments(sorted_comments, delta)

        comment_count = len(relevant_comments)
        most_recent_date = relevant_comments[0].split(": ", 1)[0].split(" ")[0] if relevant_comments else "No date"
        return comment_count, most_recent_date
    
    def tableview_title_for_header(self, tableview, section):
        if hasattr(tableview.data_source, 'comments'):
            num_comments = len(tableview.data_source.comments)
            return f'Comments ({num_comments})'
        return 'Identifiers'

if __name__ == '__main__':
    app = NotesApp()
    app.present('full_screen')
