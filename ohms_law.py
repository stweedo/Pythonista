import ui
import math

class OhmCalculator(ui.View):
    def __init__(self):
        self.name = 'Ohm\'s Law Calculator'
        self.background_color = 'white'
        
        self.phase_control = ui.SegmentedControl()
        self.phase_control.segments = ['Single Phase', 'Three Phase']
        self.phase_control.frame = (40, 10, 310, 32)
        self.phase_control.selected_index = 0
        self.phase_control.action = self.calculate
        self.add_subview(self.phase_control)
        
        labels = ["Voltage (V)", "Current (I)", "Resistance (Ω)", "Power (W)", "Power Factor"]
        self.input_fields = {}
        self.labels = {}
        
        for i, label in enumerate(labels):
            lbl = ui.Label()
            lbl.text = label
            lbl.frame = (40, 60+60*i, 200, 32)
            lbl.text_color = 'blue'
            self.add_subview(lbl)
            self.labels[label] = lbl
            
            tf = ui.TextField()
            tf.frame = (210, 60+60*i, 140, 32)
            tf.keyboard_type = ui.KEYBOARD_DECIMAL_PAD
            tf.name = label
            tf.border_width = 1
            tf.border_color = 'gray'
            self.add_subview(tf)
            self.input_fields[label] = tf
        
        btn = ui.Button(title='Calculate')
        btn.frame = (80, 380, 100, 32)
        btn.background_color = 'blue'
        btn.tint_color = 'white'
        btn.corner_radius = 10
        btn.action = self.calculate
        self.add_subview(btn)
        
        clear_btn = ui.Button(title='Clear')
        clear_btn.frame = (200, 380, 100, 32)
        clear_btn.background_color = 'red'
        clear_btn.tint_color = 'white'
        clear_btn.corner_radius = 10
        clear_btn.action = self.clear
        self.add_subview(clear_btn)

    def calculate(self, sender):
		    try:
		        fields = ["Voltage (V)", "Current (I)", "Resistance (Ω)", "Power (W)", "Power Factor"]
		        values = {field: float(self.input_fields[field].text) if self.input_fields[field].text else None for field in fields}
		
		        # Use a default power factor of 1 if not provided
		        power_factor = values["Power Factor"] if values["Power Factor"] is not None else 1.0
		        V, I, R, P = values["Voltage (V)"], values["Current (I)"], values["Resistance (Ω)"], values["Power (W)"]
		        
		        # Case: Voltage and Current are known
		        if V is not None and I is not None:
		            values["Resistance (Ω)"] = V / I
		            if self.phase_control.selected_index == 0:  # Single phase
		                values["Power (W)"] = V * I * power_factor
		            else:  # Three phase
		                values["Power (W)"] = math.sqrt(3) * V * I * power_factor
		        # Case: Voltage and Resistance are known
		        elif V is not None and R is not None:
		            values["Current (I)"] = V / R
		            values["Power (W)"] = (V ** 2) / R
		        # Case: Voltage and Power are known
		        elif V is not None and P is not None:
		            values["Current (I)"] = P / (V * power_factor)
		            values["Resistance (Ω)"] = (V ** 2) / P
		        # Case: Current and Resistance are known
		        elif I is not None and R is not None:
		            values["Voltage (V)"] = I * R
		            values["Power (W)"] = (I ** 2) * R
		        # Case: Current and Power are known
		        elif I is not None and P is not None:
		            values["Voltage (V)"] = P / (I * power_factor)
		            values["Resistance (Ω)"] = (P / I ** 2)
		        # Case: Resistance and Power are known
		        elif R is not None and P is not None:
		            values["Voltage (V)"] = math.sqrt(P * R)
		            values["Current (I)"] = math.sqrt(P / R)
		
		        for field, value in values.items():
		            if value is not None:
		                self.input_fields[field].text = f"{value:.3f}".rstrip('0').rstrip('.')
		    except ValueError:
		        self.input_fields["Power (W)"].text = "Error: Please input valid numbers only."
        
    def clear(self, sender):
        for field in self.input_fields.values():
            field.text = ''
        
if __name__ == '__main__':
    view = OhmCalculator()
    view.present('sheet')
