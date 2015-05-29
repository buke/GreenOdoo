#This file is part of vatnumber.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
'''
Unit test for vatnumber
'''

import unittest
import vatnumber

VAT_NUMBERS = [
    ('AT', 'U12345675', True),
    ('AT', 'U123456789', False),
    ('AT', 'A12345675', False),
    ('AT', 'UA2345675', False),
    ('AT', 'U12345620', True),
    ('AT', 'U12345678', False),
    ('AL', 'K99999999L', True),
    ('AL', 'K999999999L', False),
    ('AL', 'AA9999999L', False),
    ('AL', 'KA9999999L', False),
    ('AL', 'K999999991', False),
    ('BE', '0123456749', True),
    ('BE', '0897290877', True),
    ('BE', '01234567490', False),
    ('BE', '9123456749', False),
    ('BE', '0A23456749', False),
    ('BE', '0123456700', False),
    ('BG', '1234567892', True),
    ('BG', '175074752', True),
    ('BG', '131202360', True),
    ('BG', '040683212', True),
    ('BG', '12345678921', False),
    ('BG', 'A234567892', False),
    ('BG', '2234567892', False),
    ('BG', '1001000000', True),
    ('BG', '0000003000', False),
    ('BG', '1234567890', False),
    ('CL', '334441113', True),
    ('CL', 'A34441113', False),
    ('CL', '334441180', True),
    ('CL', '33444113K', True),
    ('CO', '9001279338', True),
    ('CO', '900127933', False),
    ('CO', 'A001279338', False),
    ('CO', '9001279320', True),
    ('CY', '12345678F', True),
    ('CY', '2345678F', False),
    ('CY', 'A2345678F', False),
    ('CY', '12345678A', False),
    ('CZ', '1234567', False),
    ('CZ', '12345679', True),
    ('CZ', 'A2345679', False),
    ('CZ', '92345679', False),
    ('CZ', '10001000', True),
    ('CZ', '10000101', True),
    ('CZ', '12345670', False),
    ('CZ', '612345670', True),
    ('CZ', '612345679', False),
    ('CZ', '991231123', True),
    ('CZ', '541231123', False),
    ('CZ', '791231123', False),
    ('CZ', '990031123', False),
    ('CZ', '991331123', False),
    ('CZ', '995031123', False),
    ('CZ', '996331123', False),
    ('CZ', '990200123', False),
    ('CZ', '995229123', False),
    ('CZ', '965200123', False),
    ('CZ', '960230123', False),
    ('CZ', '990400123', False),
    ('CZ', '990431123', False),
    ('CZ', '990100123', False),
    ('CZ', '990132123', False),
    ('CZ', '6306150004', True),
    ('CZ', '5306150004', False),
    ('CZ', '6300150004', False),
    ('CZ', '6313150004', False),
    ('CZ', '6350150004', False),
    ('CZ', '6363150004', False),
    ('CZ', '6302000004', False),
    ('CZ', '6302290004', False),
    ('CZ', '6402000004', False),
    ('CZ', '6402310004', False),
    ('CZ', '6304000004', False),
    ('CZ', '6304310004', False),
    ('CZ', '6301000004', False),
    ('CZ', '6301320004', False),
    ('CZ', '6306150000', False),
    ('CZ', '6306150004', True),
    ('DE', '123456788', True),
    ('DE', '12345678', False),
    ('DE', 'A23456788', False),
    ('DE', '000000088', False),
    ('DE', '123456770', True),
    ('DE', '123456789', False),
    ('DK', '12345674', True),
    ('DK', '1234564', False),
    ('DK', 'A2345674', False),
    ('DK', '02345674', False),
    ('DK', '12345679', False),
    ('EE', '123456780', True),
    ('EE', '1234567890', False),
    ('EE', 'A23456780', False),
    ('EE', '123456789', False),
    ('ES', 'A12345674', True),
    ('ES', 'P1234567D', True),
    ('ES', 'K1234567L', True),
    ('ES', 'R9600075G', True),
    ('ES', 'W4003922D', True),
    ('ES', 'V99218067', True),
    ('ES', 'U99216632', True),
    ('ES', 'J99216582', True),
    ('ES', 'U99216426', True),
    ('ES', '12345678Z', True),
    ('ES', 'X5277343Q', True),
    ('ES', 'Y5277343F', True),
    ('ES', 'Z5277343K', True),
    ('ES', '1234567890', False),
    ('ES', 'AB3456789', False),
    ('ES', 'A12345690', True),
    ('ES', 'A12345679', False),
    ('ES', 'WA003922D', False),
    ('ES', 'W4003922A', False),
    ('ES', 'ZA277343K', False),
    ('ES', 'Z5277343A', False),
    ('ES', '1A345678Z', False),
    ('ES', '12345678A', False),
    ('FI', '12345671', True),
    ('FR', '32123456789', True),
    ('FR', '2H123456789', True),
    ('GB', 'GD123', True),
    ('GB', 'GD888812326', True),
    ('GB', 'HA567', True),
    ('GB', 'HA888856782', True),
    ('GB', '123456782', True),
    ('GB', '102675046', True),
    ('GB', '100190874', True),
    ('GB', '003232345', True),
    ('GB', '1234567823', True),
    ('GB', '001123456782', True),
    ('GB', '0011234567823', True),
    ('GB', '242338087388', True),
    ('GR', '12345670', True),
    ('GR', '123456783', True),
    ('HR', '12345678903', True),
    ('HR', '24595836665', True),
    ('HR', '23448731483', True),
    ('HU', '12345676', True),
    ('IE', '7A12345J', True),
    ('IE', '1234567T', True),
    ('IT', '12345670017', True),
    ('IT', '00118439991', True),
    ('LT', '123456715', True),
    ('LT', '123456789011', True),
    ('LU', '12345613', True),
    ('LV', '41234567891', True),
    ('LV', '15066312345', True),
    ('MT', '12345634', True),
    ('NL', '123456782B90', True),
    ('PL', '1234567883', True),
    ('PT', '123456789', True),
    ('RO', '24736200', True),
    ('RO', '1234567897', True),
    ('RO', '1630615123457', True),
    ('RU', '5505035011', True),
    ('RU', '550501929014', True),
    ('SE', '123456789701', True),
    ('SE', '556728341001', True),
    ('SI', '12345679', True),
    ('SK', '0012345675', True),
    ('SK', '0012345678', True),
    ('SK', '531231123', True),
    ('SK', '6306151234', True),
    ('SK', '2021853504', True),
    ('SM', '12345', True),
    ('UA', '12345678', True),
    ('', '12456789', False),
]

VIES_NUMBERS = [
    'BE0897290877',
]


class VatNumberTest(unittest.TestCase):
    '''
    Test Case for vatnumber
    '''

    def test_vat_numbers(self):
        '''
        Test VAT numbers
        '''
        for code, number, result in VAT_NUMBERS:
            if result:
                test = self.assert_
            else:
                test = self.assertFalse
            test(vatnumber.check_vat(code + number), code + number)

    def test_vies(self):
        '''
        Test vies
        '''
        for vat in VIES_NUMBERS:
            self.assert_(vatnumber.check_vies(vat))

    def test_countries(self):
        '''
        Test countries
        '''
        vatnumber.countries()

if __name__ == '__main__':
    unittest.main()
