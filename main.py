from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.relativelayout import RelativeLayout
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
import json
import os
from datetime import datetime, timedelta
try:
    from plyer import notification, vibrator
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

# Data file for persistence
DATA_FILE = 'pomodoro_data.json'

def load_data():
    default_data = {
        'settings': {'focus': 40, 'short': 5, 'long': 20, 'sessions': 4, 'theme': 'Coffee Break', 'auto_break': True, 'auto_focus': True},
        'stats': {'total_pomos': 0, 'total_time': 0, 'daily': {}, 'weekly': {}},
        'user': None,
        'last_date': None,
        'current_cycle': 0  # Pomodoros in current cycle
    }
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            for key in default_data:
                if key not in data:
                    data[key] = default_data[key]
            return data
    return default_data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Themes (background colors)
THEMES = {
    'Lavender Dreams': (0.8, 0.6, 1, 1),
    'Forest Meditation': (0.5, 0.8, 0.5, 1),
    'Ocean Breeze': (0.5, 0.8, 1, 1),
    'Sky Drift': (0.9, 0.9, 1, 1),
    'Coffee Break': (0.96, 0.87, 0.7, 1),
    'Cherry Blossom': (1, 0.8, 0.9, 1),
    'Mint Fresh': (0.7, 1, 0.8, 1),
    'Aurora Night': (0.2, 0.2, 0.5, 1),
    'Monochrome Minimal': (0.9, 0.9, 0.9, 1),
    'Nuyo Focus Dark': (0.1, 0.1, 0.1, 1)
}

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        layout.add_widget(Label(text='Sign up/Login to start Pomodoro', font_size=20))
        self.email = TextInput(hint_text='Enter email (Google/Microsoft/any)', multiline=False, size_hint_y=None, height=40)
        btn = Button(text='Continue', size_hint_y=None, height=50)
        btn.bind(on_press=self.login)
        layout.add_widget(self.email)
        layout.add_widget(btn)
        self.add_widget(layout)

    def login(self, instance):
        if self.email.text:
            data = load_data()
            data['user'] = self.email.text
            save_data(data)
            self.manager.current = 'timer'

class TimerWidget(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.time_left = 40 * 60  # Default focus
        self.is_running = False
        self.paused = False
        self.mode = 'focus'
        self.current_time = 40 * 60
        self.sound = SoundLoader.load('beep.mp3')  # Add beep.mp3 for ringtone; falls back to None

        with self.canvas:
            Color(0.96, 0.87, 0.7, 0.3)  # Beige background circle
            self.bg_circle = Ellipse(pos=self.center, size=(300, 300))
            Color(1, 1, 1, 0.5)  # White progress circle (basic)
            self.progress_circle = Ellipse(pos=self.center, size=(300, 300))

        self.time_label = Label(
            text='40:00', font_size='72sp', size_hint=(None, None), size=(200, 100),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}, color=(0, 0, 0, 1)
        )
        self.add_widget(self.time_label)

        self.bind(pos=self.update_graphics, size=self.update_graphics)
        Clock.schedule_interval(self.update_timer, 1)

    def update_graphics(self, *args):
        self.bg_circle.pos = (self.center_x - 150, self.center_y - 150)
        self.progress_circle.pos = (self.center_x - 150, self.center_y - 150)
        self.bg_circle.size = self.size
        self.progress_circle.size = self.size

    def update_timer(self, dt):
        if self.is_running and not self.paused:
            self.time_left -= 1
            mins, secs = divmod(self.time_left, 60)
            self.time_label.text = f'{mins:02d}:{secs:02d}'
            if self.time_left <= 0:
                self.complete_session()
        return True

    def toggle_play_pause(self):
        if not self.is_running:
            self.is_running = True
            self.paused = False
            return '⏸ Pause'
        elif self.paused:
            self.paused = False
            return '⏸ Pause'
        else:
            self.paused = True
            return '▶ Resume'

    def reset(self):
        self.is_running = False
        self.paused = False
        self.time_left = self.current_time
        mins, secs = divmod(self.time_left, 60)
        self.time_label.text = f'{mins:02d}:{secs:02d}'

    def complete_session(self):
        data = load_data()
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        weekday = now.strftime('%A')

        # Update stats
        data['total_pomos'] += 1 if self.mode == 'focus' else 0
        data['total_time'] += self.current_time

        if data['last_date'] != date_str:
            # New day - reset daily at midnight
            data['daily'] = {date_str: {'pomos': 1 if self.mode == 'focus' else 0, 'time': self.current_time}}
            data['last_date'] = date_str
            # Weekly reset on Monday
            if weekday == 'Monday':
                data['weekly'] = {}
        else:
            if date_str not in data['daily']:
                data['daily'][date_str] = {'pomos': 0, 'time': 0}
            data['daily'][date_str]['pomos'] += 1 if self.mode == 'focus' else 0
            data['daily'][date_str]['time'] += self.current_time

        # Weekly: sum last 7 days (simple)
        week_start = (now - timedelta(days=6)).strftime('%Y-%m-%d')
        data['weekly'] = sum(d.get('pomos', 0) for d in list(data['daily'].values())[-7:]) if len(data['daily']) >= 7 else 0

        # Cycle for long break
        if self.mode == 'focus':
            data['current_cycle'] += 1
            if data['current_cycle'] % data['settings']['sessions'] == 0:
                self.mode = 'long'
                self.current_time = data['settings']['long'] * 60
            else:
                self.mode = 'short'
                self.current_time = data['settings']['short'] * 60
        else:
            self.mode = 'focus'
            self.current_time = data['settings']['focus'] * 60
            data['current_cycle'] = 0  # Reset after long break

        save_data(data)

        # Reward
        reward_msg = 'Amazing! You earned a reward: 🌟 Focus Star!' if self.mode == 'focus' else 'Great break!'
        popup = Popup(title='Session Complete!', content=Label(text=reward_msg), size_hint=(0.8, 0.4))
        popup.open()

        # Ring & Vibrate (works on lock screen)
        if self.sound:
            self.sound.play()
        if HAS_PLYER:
            notification.notify(title=f'{self.mode.title()} Complete', message=reward_msg, timeout=5)
            vibrator.vibrate(0.5)

        self.reset()

class TimerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Header
        header = BoxLayout(size_hint_y=None, height=50)
        self.mode_label = Label(text='Focus Time', size_hint_x=0.8, font_size=18)
        header.add_widget(self.mode_label)
        switch_btn = Button(text='Tap to switch', size_hint_x=0.2, disabled=True)  # Placeholder
        header.add_widget(switch_btn)
        self.layout.add_widget(header)

        # Timer
        self.timer_widget = TimerWidget(size_hint=(1, 0.6))
        self.layout.add_widget(self.timer_widget)

        # Controls
        controls = BoxLayout(size_hint_y=None, height=60, spacing=10)
        self.toggle_btn = Button(text='▶ Start', font_size=20)
        self.toggle_btn.bind(on_press=self.on_toggle)
        reset_btn = Button(text='🔄 Reset', font_size=20)
        reset_btn.bind(on_press=self.timer_widget.reset)
        controls.add_widget(self.toggle_btn)
        controls.add_widget(reset_btn)
        self.layout.add_widget(controls)

        # Bottom icons
        bottom = BoxLayout(size_hint_y=None, height=50, spacing=50)
        stats_btn = Button(text='📊 Stats')
        stats_btn.bind(on_press=lambda x: self.manager.current = 'stats')
        settings_btn = Button(text='⚙ Settings')
        settings_btn.bind(on_press=lambda x: self.manager.current = 'settings')
        bottom.add_widget(stats_btn)
        bottom.add_widget(settings_btn)
        self.layout.add_widget(bottom)

        self.add_widget(self.layout)
        self.load_settings()

    def load_settings(self):
        data = load_data()
        self.timer_widget.current_time = data['settings']['focus'] * 60
        self.timer_widget.time_left = self.timer_widget.current_time
        self.timer_widget.mode = 'focus'
        self.mode_label.text = 'Focus Time'
        Window.clearcolor = THEMES.get(data['settings']['theme'], THEMES['Coffee Break'])

    def on_toggle(self, instance):
        new_text = self.timer_widget.toggle_play_pause()
        self.toggle_btn.text = new_text

class StatsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.content = Label(text='', font_size=16, halign='left', valign='top', text_size=(None, None))
        scroll = ScrollView()
        scroll.add_widget(self.content)
        self.layout.add_widget(scroll)
        back_btn = Button(text='← Back', size_hint_y=None, height=50)
        back_btn.bind(on_press=lambda x: self.manager.current = 'timer')
        self.layout.add_widget(back_btn)
        self.add_widget(self.layout)
        Clock.schedule_once(self.refresh, 0)

    def refresh(self, dt):
        data = load_data()
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        pomos_today = data['daily'].get(today, {'pomos': 0})['pomos']
        time_today = data['daily'].get(today, {'time': 0})['time'] // 60
        total_pomos = data['stats']['total_pomos']
        total_time_h = data['stats']['total_time'] // 3600
        total_time_m = (data['stats']['total_time'] % 3600) // 60
        weekly_pomos = data['stats']['weekly']

        # Daily refresh check (simulated on load)
        if data['last_date'] != today:
            # Reset daily if past midnight
            pass  # Handled in complete

        text = f"""
All-time:
Total Pomodoros: {total_pomos}
Total Focus Time: {total_time_h}h {total_time_m}m

Today:
Pomodoros: {pomos_today}/8 (Daily Goal - Fixed)
Focus Time: {time_today // 60}h {time_today % 60}m

This Week:
Total Pomodoros: {weekly_pomos}
(Weekly resets Monday)

Detailed Analysis:
- Monthly/Yearly: Sum of daily data (implement charts later)
- Focus Sessions Completed Today: {pomos_today}
- Total Ever: {total_pomos}
"""
        self.content.text = text

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.layout.add_widget(Label(text='Timer Durations', font_size=20))

        data = load_data()

        # Focus
        focus_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        focus_row.add_widget(Label(text='Focus Time (min):'))
        self.focus_spinner = Spinner(text=str(data['settings']['focus']), values=[str(i) for i in range(1, 61)])
        focus_row.add_widget(self.focus_spinner)
        self.layout.add_widget(focus_row)

        # Short Break
        short_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        short_row.add_widget(Label(text='Short Break (min):'))
        self.short_spinner = Spinner(text=str(data['settings']['short']), values=[str(i) for i in range(1, 31)])
        short_row.add_widget(self.short_spinner)
        self.layout.add_widget(short_row)

        # Long Break
        long_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        long_row.add_widget(Label(text='Long Break (min):'))
        self.long_spinner = Spinner(text=str(data['settings']['long']), values=[str(i) for i in range(1, 61)])
        long_row.add_widget(self.long_spinner)
        self.layout.add_widget(long_row)

        # Sessions until Long
        sessions_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        sessions_row.add_widget(Label(text='Sessions until Long:'))
        self.sessions_spinner = Spinner(text=str(data['settings']['sessions']), values=[str(i) for i in range(1, 11)])
        sessions_row.add_widget(self.sessions_spinner)
        self.layout.add_widget(sessions_row)

        # Auto-start
        self.layout.add_widget(Label(text='Auto-Start', font_size=18))
        auto_break_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        self.auto_break_toggle = ToggleButton(text='Auto-start breaks after focus', state='down' if data['settings']['auto_break'] else 'normal')
        auto_break_row.add_widget(self.auto_break_toggle)
        self.layout.add_widget(auto_break_row)

        auto_focus_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        self.auto_focus_toggle = ToggleButton(text='Auto-start focus after break', state='down' if data['settings']['auto_focus'] else 'normal')
        auto_focus_row.add_widget(self.auto_focus_toggle)
        self.layout.add_widget(auto_focus_row)

        # Keep screen on (warning)
        keep_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        self.keep_toggle = ToggleButton(text='Keep screen on (Battery drain & security risk)', state='down')
        keep_row.add_widget(self.keep_toggle)
        self.layout.add_widget(keep_row)

        # Theme
        self.layout.add_widget(Label(text='Color Theme\nChoose a palette that helps you focus', font_size=18))
        self.theme_spinner = Spinner(text=data['settings']['theme'], values=list(THEMES.keys()))
        self.layout.add_widget(self.theme_spinner)

        # Ringtone & Volume (basic toggle for now)
        self.layout.add_widget(Label(text='Ringtone & Volume', font_size=18))
        ring_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        ring_row.add_widget(Label(text='Custom Ringtone:'))
        self.ring_toggle = ToggleButton(text='Enabled', state='down')  # Add MP3 later
        ring_row.add_widget(self.ring_toggle)
        self.layout.add_widget(ring_row)
        # Volume slider (placeholder)
        self.volume_slider = Slider(min=0, max=100, value=50, size_hint_y=None, height=40)
        self.layout.add_widget(Label(text='App Ringtone Volume:'))
        self.layout.add_widget(self.volume_slider)

        # Save
        save_btn = Button(text='Save Settings', size_hint_y=None, height=50)
        save_btn.bind(on_press=self.save)
        self.layout.add_widget(save_btn)

        # Backup
        export_btn = Button(text='Export Data (Backup)', size_hint_y=None, height=50)
        export_btn.bind(on_press=self.export_data)
        self.layout.add_widget(export_btn)

        import_btn = Button(text='Import Data', size_hint_y=None, height=50)
        import_btn.bind(on_press=self.import_data)
        self.layout.add_widget(import_btn)

        back_btn = Button(text='← Back', size_hint_y=None, height=50)
        back_btn.bind(on_press=lambda x: self.manager.current = 'timer')
        self.layout.add_widget(back_btn)

        self.add_widget(self.layout)

    def save(self, instance):
        data = load_data()
        data['settings']['focus'] = int(self.focus_spinner.text)
        data['settings']['short'] = int(self.short_spinner.text)
        data['settings']['long'] = int(self.long_spinner.text)
        data['settings']['sessions'] = int(self.sessions_spinner.text)
        data['settings']['auto_break'] = self.auto_break_toggle.state == 'down'
        data['settings']['auto_focus'] = self.auto_focus_toggle.state == 'down'
        data['settings']['theme'] = self.theme_spinner.text
        # Volume & ring (save for later use)
        data['settings']['volume'] = self.volume_slider.value
        data['settings']['ringtone'] = 'enabled' if self.ring_toggle.state == 'down' else 'disabled'
        save_data(data)
        # Apply theme
        Window.clearcolor = THEMES[data['settings']['theme']]
        # Refresh timer
        App.get_running_app().root.get_screen('timer').load_settings()
        popup = Popup(title='Saved!', content=Label(text='Settings updated.'), size_hint=(0.6, 0.4))
        popup.open()

    def export_data(self, instance):
        data = load_data()
        backup_file = 'pomodoro_backup.json'
        with open(backup_file, 'w') as f:
            json.dump(data, f, indent=4)
        popup = Popup(title='Exported!', content=Label(text=f'Data saved to {backup_file}'), size_hint=(0.6, 0.4))
        popup.open()

    def import_data(self, instance):
        if os.path.exists('pomodoro_backup.json'):
            with open('pomodoro_backup.json', 'r') as f:
                data = json.load(f)
                save_data(data)
            popup = Popup(title='Imported!', content=Label(text='Data restored.'), size_hint=(0.6, 0.4))
            popup.open()
            # Refresh screens
            App.get_running_app().root.get_screen('stats').refresh(0)
            App.get_running_app().root.get_screen('timer').load_settings()
        else:
            popup = Popup(title='Error', content=Label(text='No backup.json found.'), size_hint=(0.6, 0.4))
            popup.open()

class PomodoroApp(App):
    def build(self):
        Window.clearcolor = THEMES['Coffee Break']
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(TimerScreen(name='timer'))
        sm.add_widget(StatsScreen(name='stats'))
        sm.add_widget(SettingsScreen(name='settings'))
        data = load_data()
        sm.current = 'login' if not data['user'] else 'timer'
        return sm

if __name__ == '__main__':
    PomodoroApp().run()
