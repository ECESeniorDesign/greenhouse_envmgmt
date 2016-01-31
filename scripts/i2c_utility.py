#!/usr/bin/python
# This file contains utility functions used to select
# 	channels via the I2C Multiplexer or the ADC

def TCA_select(bus, addr, channel):
    """
        This function will write to the control register of the
                TCA module to select the channel that will be
                exposed on the TCA module.
        After doing this, the desired module can be used as it would be normally.
                (The caller should use the address of the I2C sensor module.
        The TCA module is only written to when the channel is switched.)
                addr contains address of the TCA module
                channel specifies the desired channel on the TCA that will be used.

        Usage - Enable a channel
            TCA_select(bus, self.mux_addr, channel_to_enable)
                Channel to enable begins at 0 (enables first channel)
                                    ends at 3 (enables fourth channel)

        Usage - Disable all channels
            TCA_select(bus, self.mux_addr, "off")
                This call must be made whenever the sensor node is no longer
                    being accessed.
                If this is not done, there will be addressing conflicts.
    """
    if addr < 0x70 or addr > 0x77:
        print("The TCA address(" + str(addr) + ") is invalid. Aborting")
        return False
    if channel == "off":
        bus.write_byte(addr, 0)
    elif channel < 0 or channel > 3:
        print("The requested channel does not exist.")
        return False
    else:
        bus.write_byte(addr, 1 << channel)

    status = bus.read_byte(addr)
    return status


def get_ADC_value(bus, addr, channel):
    """
    This method selects a channel and initiates conversion

    Usage - ADC_start(bus, self.ADC_addr, channel_to_enable)

    """
    print("The ADC is not yet configured")


def GPIO_update_output(bus, addr, bank, mask):
    """
    Method for controlling the GPIO expander via I2C
        which accepts a bank - A(0) or B(1) and a mask
        to push to the pins of the expander.

    The method also assumes the the expander is operating
        in sequential mode. If this mode is not used,
        the register addresses will need to be changed.

    Usage:
    GPIO_out(bus, GPIO_addr, 0, 0b00011111)
        This call would turn on A0 through A4. 

    """
    IODIR_map = [0x00, 0x01]
    OutputMap = [0x14, 0x15]

    if (bank != 0) and (bank != 1):
        print()
        raise Expection("An invalid IO bank has been selected")

    IO_direction = IODIR_map[bank]
    OutputRegister = OutputMap[bank]

    currentStatus = bus.read_byte_data(addr, OutputRegister)
    if currentStatus == mask:
        # This means nothing needs to happen
        print("Current control status matches requested controls. " +
              "No action is required.")
        return True

    bus.write_byte_data(addr, IO_direction, 0)
    bus.write_byte_data(addr, OutputRegister, mask)
