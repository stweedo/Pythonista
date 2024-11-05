import ui
import sqlite3
from datetime import datetime, timedelta
from functools import lru_cache
import re

DB_FILENAME = 'ants.db'
DATESTR = '%m-%d-%Y %H:%M:%S'

class SearchIndex:
    def __init__(self):
        self.index = {}
        self.id_index = {}
    
    def add_entry(self, identifier, timestamp, comment):
        # Add to comment index
        words = set(re.findall(r'\w+', comment.lower()))
        for word in words:
            if word not in self.index:
                self.index[word] = set()
            self.index[word].add((identifier, timestamp, comment))
        
        # Add to ID index
        id_parts = set(identifier.lower().split())
        for part in id_parts:
            if part not in self.id_index:
                self.id_index[part] = set()
            self.id_index[part].add(identifier)

    def search(self, query, id_filter=None):
        if not query:
            return set()
        
        words = set(re.findall(r'\w+', query.lower()))
        if not words:
            return set()
        
        # Sort words by frequency in index to optimize intersection
        sorted_words = sorted(words, key=lambda w: len(self.index.get(w, set())))
        results = self.index.get(sorted_words[0], set())
        
        # Early exit if no results
        if not results:
            return set()
            
        for word in sorted_words[1:]:
            word_results = self.index.get(word, set())
            results &= word_results
            if not results:  # Early exit if intersection is empty
                break
                
        if id_filter:
            results = {r for r in results if r[0] == id_filter}
                
        return results
    
    def search_ids(self, query):
        if not query:
            return set()
        
        words = set(re.findall(r'\w+', query.lower()))
        if not words:
            return set()
        
        results = self.id_index.get(next(iter(words)), set())
        
        for word in words:
            word_results = self.id_index.get(word, set())
            results &= word_results
            
        return results

class NotesApp(ui.View):
    def __init__(self):
        super().__init__()
        self.search_index = SearchIndex()
        self.setup_database()
        self.load_notes()
        self.updating_comment_index = None
        self.is_comment_search_active = False
        self.clear_state = 0
        self.create_ui_elements()
        self.filter_notes(None)

    def load_notes(self):
        with sqlite3.connect(DB_FILENAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp, comment FROM notes")
            self.notes = {}
            for id, timestamp, comment in cursor.fetchall():
                self.notes.setdefault(id, []).append(f"{timestamp}: {comment}")
                self.search_index.add_entry(id, timestamp, comment)
        self.original_notes = dict(self.notes)
        self.displayed_notes = dict(self.notes)

    def filter_notes(self, sender):
        current_id = self.id_input.text.strip()
        comment_query = self.comment_input.text.strip()
        
        self.is_comment_search_active = bool(comment_query)
        delta = self.get_timeframe_delta(self.timeframe_control.selected_index)
        
        self.displayed_notes = {}
        
        if comment_query:
            # Search by comment content
            results = self.search_index.search(comment_query, current_id if current_id else None)
            for identifier, timestamp, comment in results:
                if self._is_within_timeframe(timestamp, delta):
                    self.displayed_notes.setdefault(identifier, []).append(f"{timestamp}: {comment}")
        elif current_id:
            # Search by ID
            matching_ids = self.search_index.search_ids(current_id)
            for id in matching_ids:
                relevant_comments = self._filter_comments_by_timeframe(self.notes[id], delta)
                if relevant_comments:
                    self.displayed_notes[id] = relevant_comments
        else:
            # Show all notes within timeframe
            for id, comments in self.notes.items():
                relevant_comments = self._filter_comments_by_timeframe(comments, delta)
                if relevant_comments:
                    self.displayed_notes[id] = relevant_comments
        
        self.update_notes_list()
        ui.end_editing()

    def _is_within_timeframe(self, timestamp_str, delta):
        if not delta:
            return True
        timestamp = datetime.strptime(timestamp_str, DATESTR)
        return datetime.now() - timestamp < delta

    def _filter_comments_by_timeframe(self, comments, delta):
        if not delta:
            return comments
        return [comment for comment in comments 
                if datetime.now() - datetime.strptime(comment.split(": ", 1)[0], DATESTR) < delta]

    @staticmethod
    @lru_cache(maxsize=None)
    def create_button(title, bg_color, action):
        btn = ui.Button(title=title, background_color=bg_color, tint_color='white', corner_radius=10)
        btn.action = action
        return btn

    def setup_database(self):
        with sqlite3.connect(DB_FILENAME) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT,
                    timestamp TEXT,
                    comment TEXT
                )
            ''')

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
        self.notes_list.frame = (w // 2, 10, w // 2 - 10, h - 20) if w > h else (10, 335, 370, 385)
        if w > h:
            ui.end_editing()

    def setup_ui_properties(self):
        self.name = 'Advanced Note Taking System'
        self.background_color = 'white'

    def add_identifier_input(self):
        self.id_input = ui.TextField(frame=(10, 10, 370, 32), placeholder='Unique identifier (Asset number)', 
                                     font=('<system-bold>', 20), alignment=ui.ALIGN_CENTER, continuous=True)
        self.add_subview(self.id_input)

    def add_comment_label(self):
        self.comment_label = ui.Label(frame=(10, 55, 370, 20), text="Comment:")
        self.add_subview(self.comment_label)

    def add_comment_input(self):
        self.comment_input = ui.TextView(frame=(10, 85, 370, 120), border_width=1, corner_radius=8, font=('<system>', 17))
        self.add_subview(self.comment_input)

    def add_dynamic_button(self):
        self.dynamic_button = self.create_button('Search', 'blue', self.filter_notes)
        self.dynamic_button.frame = (70, 225, 100, 40)
        self.add_subview(self.dynamic_button)

    def update_dynamic_button(self, title, action):
        self.dynamic_button.title = title
        self.dynamic_button.action = action

    def add_clear_button(self):
        self.clear_button = self.create_button('Clear', 'red', self.clear_input)
        self.clear_button.frame = (220, 225, 100, 40)
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

    def input_change(self, sender):
        if sender == self.id_input:
            self.filter_notes(None)
        elif sender == self.comment_input:
            id_text = self.id_input.text.strip()
            comment_text = self.comment_input.text.strip()
            action = self.save_note if id_text and comment_text else self.filter_notes
            self.update_dynamic_button('Save' if id_text and comment_text else 'Search', action)

    @staticmethod
    @lru_cache(maxsize=4)
    def get_timeframe_delta(timeframe):
        if timeframe == 1:  # Day
            return timedelta(days=1)
        elif timeframe == 2:  # Week
            return timedelta(days=7)
        elif timeframe == 3:  # Month
            return timedelta(days=30)
        return None

    @staticmethod
    def sort_comments(comments):
        return sorted(comments, key=lambda x: datetime.strptime(x.split(": ", 1)[0], DATESTR), reverse=True)

    def get_relevant_comments(self, comments, delta=None, query=None):
        now = datetime.now().date()
        filtered_comments = comments

        if delta is not None:
            filtered_comments = [comment for comment in filtered_comments 
                                 if now - datetime.strptime(comment.split(": ", 1)[0], DATESTR).date() < delta]

        if query and self.is_comment_search_active:
            filtered_comments = [comment for comment in filtered_comments if query.lower() in comment.lower()]

        return self.sort_comments(filtered_comments)

    def update_notes_list(self):
        if self.displayed_notes and self.id_input.text in self.displayed_notes:
            self.notes_list.data_source.comments = self.displayed_notes[self.id_input.text]
        elif hasattr(self.notes_list.data_source, 'comments'):
            delattr(self.notes_list.data_source, 'comments')
        self.notes_list.reload()

    def save_notes_to_db(self, identifier, comments):
        with sqlite3.connect(DB_FILENAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (identifier,))
            cursor.executemany("INSERT INTO notes (id, timestamp, comment) VALUES (?, ?, ?)", 
                               [(identifier, *comment.split(": ", 1)) for comment in comments])
        self.load_notes()
        self.notes_list.reload()

    def clear_comment_input(self):
        self.comment_input.text = ''
        self.updating_comment_index = None
        self.notes_list.selected_row = -1
        self.is_comment_search_active = False

    def clear_input(self, sender):
        if self.comment_input.text:
            self.clear_comment_input()
        elif self.id_input.text:
            self.clear_id_input()
        self.filter_notes(None)
        self.update_dynamic_button('Search', self.filter_notes)
        ui.end_editing()

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
        self.save_notes_to_db(identifier, self.notes[identifier])
        self.filter_notes(None)
        ui.end_editing()

    def refresh_comments_list(self, identifier):
        if hasattr(self.notes_list.data_source, 'comments'):
            sorted_comments = self.get_relevant_comments(self.notes[identifier])
            self.notes_list.data_source.comments = sorted_comments
            self.notes_list.reload()

    def delete_entry(self, identifier=None, comment_index=None):
        if comment_index is not None:
            del self.notes[identifier][comment_index]
            if not self.notes[identifier]:
                del self.notes[identifier]
        elif identifier:
            del self.notes[identifier]
        self.save_notes_to_db(identifier, self.notes.get(identifier, []))

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
                delta = self.get_timeframe_delta(self.timeframe_control.selected_index)
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
        self.save_notes_to_db(identifier, self.notes.get(identifier, []))
        self.filter_notes(None)
        tableview.reload()

    def tableview_number_of_sections(self, tableview):
        if self.is_comment_search_active:
            return max(1, len(self.displayed_notes))
        return 1  # Default to one section for normal ID display or specific ID match

    def tableview_number_of_rows(self, tableview, section):
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
                return len(exact_match_comments)
            matching_ids = [key for key in self.displayed_notes.keys() if key.lower().startswith(current_id_input)]
            return len(matching_ids)

        return len(self.displayed_notes)

    def tableview_title_for_header(self, tableview, section):
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
                cell.detail_text_label.text = comment
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
        timestamp, comment = comment_data.split(": ", 1)
        return timestamp, comment

    def extract_identifier_data(self, identifier):
        if self.comment_input.text.strip():
            relevant_comments = [comment for comment in self.displayed_notes[identifier] if self.comment_input.text.lower().strip() in comment.lower()]
        else:
            relevant_comments = self.displayed_notes.get(identifier, [])

        comment_count = len(relevant_comments)
        if relevant_comments:
            most_recent_datetime = relevant_comments[0].split(": ", 1)[0]
            most_recent_date = most_recent_datetime.split(" ")[0]  # Extract only the date part
        else:
            most_recent_date = "No date"
        return comment_count, most_recent_date

class CustomAlert(ui.View):
    def __init__(self, save_callback):
        super().__init__()
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

        update_btn = NotesApp.create_button('Update', 'red', self.update_action)
        update_btn.frame = (30, 70, 100, 40)
        self.add_subview(update_btn)

        keep_btn = NotesApp.create_button('Keep', 'blue', self.keep_action)
        keep_btn.frame = (170, 70, 100, 40)
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

if __name__ == '__main__':
    app = NotesApp()
    app.present('full_screen')
