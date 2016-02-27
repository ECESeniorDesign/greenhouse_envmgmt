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
    The ADC operates at 240 SPS (12 bits) with 1x gain
        One shot conversions are used, meaning a wait period is needed
        in order to acquire new data. This is done via a constant poll
        of the ready bit.
    Upon completion, a ratiomeric value is returned to the caller.

    Usage - ADC_start(bus, SensorCluster.ADC_addr, channel_to_read)

    """
    if channel == 1:
        INIT = 0b10000000
    elif channel == 2:
        INIT = 0b10100000
    elif channel == 3:
        INIT = 0b11000000
    elif channel == 4:
        INIT = 0b11100000
    bus.write_byte(addr, INIT)
    data = bus.read_i2c_block_data(addr, 0, 3)
    status = (data[2] & 0b10000000) >> 7
    while(status == 1):
        data = bus.read_i2c_block_data(addr, 0, 3)
        status = (data[2] & 0b10000000) >> 7
    sign = data[0] & 0b00001000
    val = ((data[0] & 0b0000111) << 8) | (data[1])
    if (sign == 1):
        val = (val ^ 0x3ff) + 1  # compute 2s complement for 12 bit val
    # Convert val to a ratiomerical ADC reading
    return float(val) / float(2047)


def IO_expander_output(bus, addr, bank, mask):
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
    output_map = [0x14, 0x15]

    if (bank != 0) and (bank != 1):
        print()
        raise InvalidIOUsage("An invalid IO bank has been selected")


    IO_direction = IODIR_map[bank]
    output_reg = output_map[bank]

    current_status = bus.read_byte_data(addr, output_reg)
    if current_status == mask:
        # This means nothing needs to happen
        print("Current control status matches requested controls. " +
              "No action is required.")
        return True

    bus.write_byte_data(addr, IO_direction, 0)
    bus.write_byte_data(addr, output_reg, mask)

def get_IO_reg(bus, addr, bank):
    """
    Method retrieves the register corresponding to respective bank (0 or 1)
    """
    output_map = [0x14, 0x15]
    if (bank != 0) and (bank != 1):
        print()
        raise InvalidIOUsage("An invalid IO bank has been selected")

    output_reg = output_map[bank]
    current_status = bus.read_byte_data(addr, output_reg)
    return current_status

def import_i2c_addr(bus, opt=None):
    """ import_i2c_addresses will return a list of the
            currently connected I2C devices.

        This can be used a means to automatically detect
            the number of connected sensor modules.
        Modules are between int(112) and int(119)
    """

    i2c_list = []
    for device in range(128):
        try:
            bus.read_byte(device)
            i2c_list.append((device))
        except IOError:
            pass

    if opt == "sensors":
        sensor_list = []
        for module in range(112,120):
            try:
                indx = i2c_list.index(module)
                sensor_list.append(module)
            except ValueError:
                pass
        return sensor_list

    else:
        return i2c_list


class InvalidIOUsage(Exception):
    pass