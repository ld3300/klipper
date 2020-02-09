# MCP4451 digipot code
#
# Copyright (C) 2018  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import bus

class I2CDevice(object):
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[1]
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.event_gcode = self.insert_gcode = None
        self.i2c = bus.MCU_I2C_from_config(config)
        i2c_addr = self.i2c.get_i2c_address()
        self.buttons = self.printer.try_load_module(config, 'buttons')
        gcode_macro = self.printer.try_load_module(config, 'gcode_macro')

        
        
        if config.get('event_gcode', None) is not None:
            self.insert_gcode = gcode_macro.load_template(
                config, 'event_gcode')
                

        
        
    def _attention_event_handler(self, eventtime):
        if self.event_running:
            return
        self.event_running = True
        self._exec_gcode(self.event_gcode)
        self.event_running = False
    def _exec_gcode(self, template):
        try:
            self.gcode.run_script(template.render() + "\nM400")
        except Exception:
            logging.exception("Script running error")
    cmd_QUERY_ATTENTION_PIN_help = "Query the status of the i2c Attention Pin"
    def cmd_QUERY_ATTENTION_PIN(self, params):
        raise NotImplementedError(
            "Sensor must implement cmd_QUERY_ATTENTION_PIN")
    cmd_I2C_SET_help = "Send an I2c command I2C_SET R=(Register) V=(Value)"
    def cmd_I2C_SET(self, params):
        raise NotImplementedError(
            "Sensor must implement cmd_I2C_SET")




        attention_pin = config.get('attention_pin')
        self.buttons.register_buttons([attention_pin], self._button_handler)
        self.start_time = self.reactor.NEVER
        self.last_attention_state = False
        self.last_cb_event_time = 0.
        self.gcode.register_mux_command(
            "QUERY_ATTENTION_PIN", "DEVICE", self.name,
            self.cmd_QUERY_ATTENTION_PIN,
            desc=self.cmd_QUERY_ATTENTION_PIN_help)
        self.gcode.register_mux_command(
            "I2C_SET", "REGISTER", self.name,
            self.cmd_I2C_SET,
            desc=self.cmd_I2C_SET_help)
        self.printer.register_event_handler("klippy:ready", self._handle_ready)
    def _handle_ready(self):
        self.start_time = self.reactor.monotonic() + 2.
    def _button_handler(self, eventtime, state):
        if eventtime < self.start_time or state == self.last_attention_state:
            self.last_attention_state = state
            return
        if state:
            # Attention pulled
            self.last_cb_event_time = eventtime
            logging.info(
                "attention_switch: event detected, Time %.2f",
                    eventtime)
            self.reactor.register_callback(self._attention_event_handler)
        self.last_attention_state = state
    def cmd_QUERY_ATTENTION_PIN(self, params):
        if self.last_attention_state:
            msg = "I2C Attention Active"
        else:
            msg = "I2C Attention Inactive"
        self.gcode.respond_info(msg)
    def cmd_I2C_SET(self, params):
        # Parse parameters
        register = self.gcode.get('R')
        value = self.gcode.get('V')
        # Send command
        self.set_register(register, value)
    def set_register(self, reg, value):
        self.i2c.i2c_write([(reg << 4) | ((value >> 8) & 0x03), value])

def load_config_prefix(config):
    return I2CDevice(config)
        

# config section needs:
# event_gcode
# attention_pin
# i2c_address
# attention_register