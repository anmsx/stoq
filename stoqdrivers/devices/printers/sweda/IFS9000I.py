# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2005 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s):   Evandro Vale Miquelito      <evandro@async.com.br>
##
"""
stoqdrivers/devices/printers/sweda/IFS9000I.py:
    
    Sweda IFS9000I printer driver implementation. 
"""

import string
import datetime

from zope.interface import implements

from stoqdrivers.common import is_float
from stoqdrivers.constants import (TAX_SUBSTITUTION, UNIT_WEIGHT, UNIT_METERS,
                                   UNIT_LITERS, UNIT_EMPTY)
from stoqdrivers.exceptions import (PrinterError, CloseCouponError,
                                    PendingReadX, CommandError,
                                    CouponOpenError, CommandParametersError,
                                    CouponNotOpenError, ReduceZError,
                                    HardwareFailure, DriverError,
                                    OutofPaperError, PendingReduceZ,
                                    InvalidState)
from stoqdrivers.devices.printers.interface import ICouponPrinter
from stoqdrivers.devices.serialbase import SerialBase
from stoqdrivers.constants import MONEY_PM, CHEQUE_PM
from stoqdrivers.devices.printers.capabilities import Capability

payment_methods = {
    MONEY_PM : "01",
    # FIXME: This value will changed after bug #2246 is fixed
    CHEQUE_PM : "01" 
}

class IFS9000I(SerialBase):

    implements(ICouponPrinter)

    printer_name = "Sweda IFS 9000 I"

    CMD_PREFIX = "."
    CMD_SUFFIX = EOL_DELIMIT = '}'
    DEBUG_MODE = 0

    #
    # Printer command set
    #
    
    CMD_COUPON_OPEN = '17'
    CMD_COUPON_ADD_ITEM = '01'
    CMD_ITEM_ADD_DISCOUNT = '02'
    CMD_ITEM_CANCEL = '04'
    CMD_COUPON_ADD_DISCOUNT = '03'
    CMD_COUPON_ADD_CHARGE = '11'
    CMD_COUPON_CANCEL = '05'
    CMD_COUPON_TOTALIZE = '10'
    CMD_COUPON_CLOSE = '12'
    CMD_READ_X = '13'
    CMD_REDUCE_Z = '14'
    CMD_PRINTER_STATUS = '23'
    CMD_PRINT_PARAMETERS = '18'
    CMD_SET_SALE_PARAMETERS = '30'
    CMD_SET_HEADER_PARAMETERS = '31'
    CMD_SAVE_USER_SETTINGS = '41'
    CMD_ADD_USER_SETTINGS = '34'
    CMD_SETUP_CLOCK = '35'
    CMD_SETUP_PAYMENT_METHOD = '39'
    CMD_TRANSACTION_STATUS = '28'
    
    #
    # Settings for printer command parameters
    #

    CUSTOMER_CHAR_LEN = 20
    CUSTOMER_CNPJ_LEN = 22
    CUSTOMER_STATE_REGISTER_LEN = 21
    # We have actually 24 characters for product descriptions but the first
    # argument define the label for product units
    DESCRIPTION_CHAR_LEN = 23
    # A second description allowed when adding items
    SECONDDESC_CHAR_LEN = 40
    PRODUCT_CODE_CHAR_LEN = 13
    TAXCODE_CHAR_LEN = 3
    PRINT_ONE_LINE_CHAR_LEN = 2
    PERCENTAGE_CHAR_LEN = 4
    ITEM_NUMBER_CHAR_LEN = 3
    PAYMENTMETHOD_CHAR_LEN = 2

    CHARGE_CHAR_LEN = 11
    CHARGE_DEC_SEPARATOR = 2
    CHARGE_ZERO_DIGITS = 0

    PRICE_CHAR_LEN = 8
    PRICE_DEC_SEPARATOR = 2
    PRICE_ZERO_DIGITS = 1

    TOTAL_CHAR_LEN = 8
    TOTAL_DEC_SEPARATOR = 2
    TOTAL_ZERO_DIGITS = 4

    QTY_CHAR_LEN = 7
    QTY_DEC_SEPARATOR= 3
    QTY_ZERO_DIGITS = 0

    # This code must be added in command CMD_COUPON_ADD_CHARGE and
    # represents a label 'ACRESCIMO' in the printed coupon
    STANDARD_CHARGE_CODE ='51'

    unit_indicators = {}
    unit_indicators[UNIT_WEIGHT] = '!'
    unit_indicators[UNIT_METERS] = '@'
    unit_indicators[UNIT_LITERS] = ')'
    unit_indicators[UNIT_EMPTY]  = '^'

    errors_dict = {'DIA ENCERRADO' : (PendingReadX, "A Read X is pending"),
                   'ERRO-COMAND INVALIDO' : (CommandError, ("The command is "
                                                            "invalid")),
                   'ERRO-OPERACAO NAO ENCERRADA' : (CouponOpenError, 
                                                    "A coupon already exist"),
                   'ERRO-PARAMETROS DO COMAND INVALIDOS' : (CommandParametersError,
                                                            "Parameters invalid."),
                   'ERRO-OPERACAO NAO ABERTA' : (CouponNotOpenError,
                                                 "There is no coupon opened"),
                   'JA  FEZ REDU��O' : (ReduceZError, "Reduce Z already done."),
                   '^RELOGIO ZERADO-PROGRAMAR' : (PrinterError,
                                                  ("Printer clock isn't "
                                                   "programmed yet.")),
                   'RELOGIO:ERRO-PROGRAMAR DATA/HORA' : (PrinterError,
                                                         ("Printer clock isn't "
                                                         "programmed yet.")),
                   '^CHAMAR ASSISTENCIA TECNICA' : (HardwareFailure,
                                                    "Problem in fiscal printer"),
                   '^CMOS: ERRO-MEM�RIA TAXAS/PARAMET' : (HardwareFailure,
                                                          ("Problem in fiscal "
                                                          "printer")),
                   'ERRO-TOTAL: NAO HOUVE LANCAMENTO' : (CloseCouponError,
                                                         ("There is no items "
                                                          "added to coupon")),
                   'ERRO - VERIFICAR PAPEL' : (OutofPaperError, "Out of paper"),
                   'ENCERRAR O DIA !' : (PendingReduceZ, ("A Reduce Z is "
                                                          "pending")),
                   'ERRO-COMANDO NAO PERMITIDO' : (InvalidState,
                                                   ("Invalid state for command "
                                                    "execution"))}

    #
    # Initializing Fiscal Printer
    #

    def setup_coupon_header(self, jump_lines_number, 
                            header_data):
        """Call this method only in non-fiscal mode.
        header_data is a list of 5 strings of 40 characters which will be
        added in the header of all the printed coupons"""
        command = self.CMD_SET_HEADER_PARAMETERS
        # This is standard. The first argument must be always 'S'
        command += 'S'
        jump_lines_number = str(jump_lines_number)
        if not jump_lines_number.isdigit():
            raise TypeError('Argument jump_lines_number must be numeric')
        if not jump_lines_number.isdigit() in range(10):
            raise TypeError('Argument jump_lines_number must be between '
                            '0 and 9')
        command += jump_lines_number
        # Here we are setting the header lines, five groups where the first
        # element is printer attribute and the second one is a the line
        # format
        if not isinstance(header_data, list):
            raise TypeError('header_data argument must be a list')
        if not len(header_data) == 5:
            raise ValueError('header_data argument must have 5 items')
        for line in header_data:
            # The first element(zero) is a default printer attribute
            command += '0%s' % line
        self.writeline(command)

    def setup_clock(self):
        t = datetime.datetime.now()

        hour = self._format_datetime(t.hour)
        minute = self._format_datetime(t.minute)
        second = self._format_datetime(t.second)
        day = self._format_datetime(t.day)
        month = self._format_datetime(t.month)
        year = str(t.year)[2:]

        time = '%s%s%s' % (hour, minute, second)
        date = '%s%s%s' % (day, month, year)

        command = self.CMD_SETUP_CLOCK + time +  date
        self.writeline(command)

    def setup_sale_parameters(self, use_cents, has_title):
        command = self.CMD_SET_SALE_PARAMETERS 
        if use_cents:
            use_cents = 'S'
        else:
            use_cents = 'N'
        if has_title:
            has_title = 'S'
        else:
            has_title = 'N'
        # standard argument for a decimal number.
        # XXX I still don't understand what is it for
        command = (self.CMD_SET_SALE_PARAMETERS + use_cents + '245' +
                   has_title)
        self.writeline(command)

    def setup_printer_user(self, user_cnpj, user_state_reg):
        # XXX Warning: never call this command more than 5 times, otherwise
        # the fiscal print will not work anymore
        command = self.CMD_ADD_USER_SETTINGS
        cnpj = self._format_string(user_cnpj, self.CUSTOMER_CNPJ_LEN, 
                                   'user_cnpj')
        state_reg = self._format_string(user_state_reg,
                                        self.CUSTOMER_STATE_REGISTER_LEN,
                                        'user_state_reg')
        command += cnpj + state_reg
        self.writeline(command)

        # Save in memory user information
        command = self.CMD_SAVE_USER_SETTINGS
        # This is a confirm argument. 'S' = confirm, 'N' = cancel
        command += 'S'
        self.writeline(command)

    def setup_sale_data(self):
        """Call this method only in non-fiscal mode."""

        # Set taxes table
        self.writeline('33T010500')
        
        # Set non-fiscal operation label
        label = '&NAO FISCAL    '
        assert len(label) == 15
        command = '38S%s' % label
        self.writeline(command)

        #
        # Setting up the payment methods
        #
        for method in (MONEY_PM, CHEQUE_PM):
            label = ("%-15s" % method.get_description())[:15]
            self.send_command(self.CMD_SETUP_PAYMENT_METHOD, 'S', label)

    #
    # Formatting data
    #

    def _check_integer(self, value, arg_name):
        value_str = str(value)
        if not value_str.isdigit():
            raise ValueError('Argument %s must be integer' % arg_name)
            
    def _check_float(self, value, arg_name):
        if not is_float(value):
            raise ValueError('Argument %s must be float' % arg_name)

    def _format_datetime(self, value):
        value = str(value)
        if len(value) == 1:
            return '0' + value
        return value

    def _format_string(self, value, arg_len, arg_name='', left_justify=False):
        value = str(value)
        if len(value) > arg_len:
            raise ValueError('Argument %s can not have more than %d '
                             'characters' % (arg_name, arg_len))
        if left_justify:
            return string.ljust(value, arg_len)
        return string.rjust(value, arg_len)

    def _format_float(self, value, arg_name, char_len, dec_separator,
                      zero_digits):
        """ - char_len is the maximum amount of character allowed for value
              argument.
            - dec_separator is the number of decimal separator digits
            - zero_digits is the number of zeros we should add in the
              beggining of the argument value """
        self._check_float(value, arg_name)
        value = '%.*f' % (dec_separator, value)
        
        # As we are going do remove the period character we can here allow
        # char_len + 1 as the maximum number of chars per argument
        value = self._format_string(value, char_len + 1, arg_name)
        value = string.replace(value, ' ', '0')
        value = string.replace(value, '.', '')

        # The first character for total and price arguments must 
        # be always zero
        value = '0' * zero_digits + value
        return value

    def _format_price(self, price, arg_name):
        return self._format_float(price, arg_name, self.PRICE_CHAR_LEN,
                                  self.PRICE_DEC_SEPARATOR, 
                                  self.PRICE_ZERO_DIGITS)

    def _format_quantity(self, quantity, arg_name):
        return self._format_float(quantity, arg_name, self.QTY_CHAR_LEN,
                                  self.QTY_DEC_SEPARATOR, 
                                  self.QTY_ZERO_DIGITS)

    def _format_total(self, total, arg_name):
        return self._format_float(total, arg_name, self.TOTAL_CHAR_LEN,
                                  self.TOTAL_DEC_SEPARATOR, 
                                  self.TOTAL_ZERO_DIGITS)

    #
    # Helper methods
    # 

    def get_transaction_status(self):
        reply = self.writeline(self.CMD_TRANSACTION_STATUS)
        if reply[1] == '+':
            return reply[2:]
        return None

    def send_command(self, command, *params):
        """ Send a command to printer.

        command: Is the command in string format
        params: a list of parameter to this command (all parameters 
        must be string)
        """
        reply = self.writeline(command + ''.join(params))
        return self.handle_error(reply)

    def handle_error(self, reply):
        # Page 4-2
        # format: |.-NNNNERROR_MESSAGE}|
        if reply[1] != '-':
            return reply[2:]
        errmsg = reply[6:]
        try:
            exception, reason = self.errors_dict[errmsg]
            raise exception(reason)
        except KeyError:
            raise DriverError(errmsg)

    def get_last_item_id(self):
        # Man page 4-62
        rv = self.get_transaction_status()
        if rv is not None:
            return int(rv[4:7])
        return rv

    def get_totalized_value(self):
        # Man page 4-63
        rv = self.get_transaction_status()
        if rv is not None:
            return float(rv[19:31]) / 1e2
        return rv

    def get_remainder_value(self):
        # Man page 4-63
        rv = self.get_transaction_status()
        if rv is not None:
            value = float(rv[31:43]) / 1e2
            if value < 0.00:
                return 0.00
        return rv

    #
    # ICouponPrinter implementation
    #

    def coupon_identify_customer(self, customer, address, document):
        # The arguments customer and address are here only for API
        # compatibility, they are not supported by the printer.
        self._customer_document = document

    def coupon_open(self):
        if self._customer_document:
            customer = self._format_string(self._customer_document,
                                           self.CUSTOMER_CHAR_LEN,
                                           'customer_document')
        else:
            customer = ''
        try:
            self.send_command(self.CMD_COUPON_OPEN, customer)
        except InvalidState:
            # if we catch InvalidState here, probably the printer is with
            # a read X pending, so..
            raise PendingReadX("A read X is pending.")

    def coupon_add_item(self, code, quantity, price, unit, description, 
                        taxcode, dicount, charge):

        if not self.unit_indicators.has_key(unit):
            raise ValueError('Invalid unit argument. Got %s' % unit)

        unit_code = self.unit_indicators[unit]
        code = self._format_string(code, self.PRODUCT_CODE_CHAR_LEN, 'code')

        orig_qty = quantity
        quantity = self._format_quantity(quantity, 'quantity')
        orig_price = price
        price = self._format_price(price, 'price')

        total = orig_qty * orig_price
        total = self._format_total(total, 'total')
        
        # TODO We need to allow using other tax codes here
        if taxcode == TAX_SUBSTITUTION:
            taxcode = 'F'
        else:
            taxcode = 'I'
        taxcode = self._format_string(taxcode, 3, 'taxcode',
                                      left_justify=True)

        description = str(description)
        if len(description) > self.DESCRIPTION_CHAR_LEN:
            second_desc = description[self.DESCRIPTION_CHAR_LEN:]
            description = description[:self.DESCRIPTION_CHAR_LEN]
        else:
            second_desc = ''
        description = self._format_string(description,
                                          self.DESCRIPTION_CHAR_LEN, 
                                          'description')
        if second_desc:
            second_desc = self._format_string(second_desc,
                                              self.SECONDDESC_CHAR_LEN, 
                                              'second_desc')
        self.send_command(self.CMD_COUPON_ADD_ITEM, code, quantity, 
                          price, total, unit_code, description, taxcode, 
                          second_desc)

        return self.get_last_item_id()

    def coupon_cancel_item(self, item_id):
        self._check_integer(item_id, 'item_id')
        item_id = self._format_string(item_id, self.ITEM_NUMBER_CHAR_LEN, 
                                      'item_id')
        item_id = string.replace(item_id, ' ', '0')

        self.send_command(self.CMD_ITEM_CANCEL, item_id)

    def coupon_add_charge(self, item_id, value, description):
        """Valid charge types are: "51": "charge"
                                   "52": "charge IOF" 
            The arguments item_id and descriptions only exit for API
            compatibility"""
        self.charge_total += value
        if not self.has_been_totalized:
            return
        elif self.charge_total == 0:
            return

        charge_type = self.STANDARD_CHARGE_CODE
        command = self.CMD_COUPON_ADD_CHARGE
        # We are always using a discount by value for API compatibility
        percentage = '0' * self.PERCENTAGE_CHAR_LEN
        charge_total = self._format_float(self.charge_total, 'value',
                                          self.CHARGE_CHAR_LEN, 
                                          self.CHARGE_DEC_SEPARATOR,
                                          self.CHARGE_ZERO_DIGITS)
        # It means always print a total after adding the charge
        print_total = 'S'
        self.send_command(self.CMD_COUPON_ADD_CHARGE, charge_type, percentage,
                          charge_total, print_total)

    def coupon_cancel(self):
        self.send_command(self.CMD_COUPON_CANCEL)

    def coupon_add_payment(self, payment_method, value, description=''):
        if not payment_method in payment_methods:
            raise TypeError("The payment method specified is invalid.")

        pm = payment_methods[payment_method]
        if description:
            description = '{' + description
        self.send_command(self.CMD_COUPON_TOTALIZE, pm,
                          '%012d' % int(float(value) * 1e2), description)
        return self.get_remainder_value()

    def coupon_totalize(self, discount, charge, taxcode, message=''):
        """Print the total value of the coupon.
           The taxcode argument is useless here and exists only for API
           compatibility"""

        if discount:
            self.discount_coupon(discount)
        elif charge:
            self.coupon_add_charge(None, charge, None)

        if message:
            message = '{' + message

        self.send_command(self.CMD_COUPON_TOTALIZE, message)
        return self.get_totalized_value()

    def coupon_close(self, message=''):
        self.send_command(self.CMD_COUPON_CLOSE)

    def close_till(self):
        # TODO Add a date optional argument here
        """This is 'reduce Z' in Brazil"""
        t = datetime.datetime.now()
        day = self._format_datetime(t.day)
        month = self._format_datetime(t.month)
        year = str(t.year)[2:]
        date = '%s%s%s' % (day, month, year)

        # This will print a sales report after summarizing
        print_report = 'S'

        self.send_command(self.CMD_REDUCE_Z, print_report, date)

    def summarize(self):
        """This is 'read X' in Brazil"""
        # This will print a sales report after summarizing
        print_report = 'S'

        self.send_command(self.CMD_READ_X, print_report)

    def get_status(self):
        # TODO retornar status de impress�o com string de interpreta��o.
        self.send_command(self.CMD_PRINTER_STATUS)

    def get_capabilities(self):
        return dict(item_code=Capability(max_len=13),
                    item_id=Capability(digits=3),
                    items_quantity=Capability(digits=4, decimals=3),
                    item_price=Capability(digits=6, decimals=2),
                    item_description=Capability(max_len=64),
                    payment_value=Capability(digits=10, decimals=2),
                    promotional_message=Capability(max_len=492),
                    payment_description=Capability(max_len=80),
                    customer_name=Capability(max_len=30),
                    customer_id=Capability(max_len=28),
                    customer_address=Capability(max_len=80))

    #
    # Auxiliar methods
    #

    def discount_coupon(self, value):
        # We are using a only a discount by value for API compatibility
        percentage = '0' * self.PERCENTAGE_CHAR_LEN
        value = '%012d' % int(float(value) * 1e2)

        # This will print a total right after add the discount
        print_total = 'S'

        self.send_command(self.CMD_COUPON_ADD_DISCOUNT, percentage, value,
                          print_total)

    def discount_item(self, value):
        # We are using a only a discount by value for API compatibility
        percentage = '0' * self.PERCENTAGE_CHAR_LEN
        value = self._format_price(value, 'value')

        self.send_command(self.CMD_ITEM_ADD_DISCOUNT, percentage, value)

    def print_printer_parameters(self):
        self.send_command(self.CMD_PRINT_PARAMETERS)

