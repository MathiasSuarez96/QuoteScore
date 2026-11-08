"""Patrones de las plantillas con contenido artificial, sin datos de clientes."""
import unittest
from datetime import date
from extraer_pdf import extraer_texto

class TemplateTests(unittest.TestCase):
    def test_header_destination_before_airport(self):
        e=extraer_texto('Arraial do Cabo\nDel 11 al 18 de enero de 2028 · 2 adultos\n¿Por qué viajar?\nVuelo a Río de Janeiro\nEl paquete incluye aéreo y hotel\nTOTAL · 2 PASAJEROS\nUSD 2.400\nPOR PERSONA\nUSD 1.200\nPagá con puntos Santander')
        self.assertEqual(e.campos['destino'],'Arraial do Cabo')
        self.assertEqual(e.campos['fecha_viaje'],date(2028,1,11))
        self.assertEqual(e.campos['menores'],0)
        self.assertEqual(e.campos['monto'],2400)
        self.assertNotIn('puntos',e.campos)
        self.assertNotIn('canal',e.campos)
        self.assertNotIn('fecha_cotizacion',e.campos)
    def test_numeric_range_and_gross_not_balance(self):
        e=extraer_texto('Playa del Carmen\n2 pasajeros · 29/12 al 05/01/2028\nEl paquete incluye hotel\nTOTAL DEL PAQUETE · 2 PASAJEROS\nUSD 3.500\nCON TUS 5.000 PUNTOS\nSALDO A PAGAR · 2 PASAJEROS\nUSD 3.100')
        self.assertEqual(e.campos['fecha_viaje'],date(2027,12,29))
        self.assertEqual(e.campos['monto'],3500)
        self.assertEqual(e.campos['puntos'],'Sí')
        self.assertNotIn('menores',e.campos)
    def test_multiple_hotels_keep_shared_fields(self):
        e=extraer_texto('Río de Janeiro\nFECHAS\n20 al 23 de diciembre\n3 noches · 2028\nVIAJAN\n2 adultos + 1 niña\nEl paquete incluye aéreo\nOPCIÓN 1\nTOTAL PARA LOS 3\nUSD 2.900\nOPCIÓN 2\nTOTAL PARA LOS 3\nUSD 2.800')
        self.assertEqual(e.campos['pax'],3)
        self.assertEqual(e.campos['menores'],1)
        self.assertEqual(e.campos['fecha_regreso'],date(2028,12,23))
        self.assertNotIn('monto',e.campos)
        self.assertEqual(len(e.opciones_precio),2)
    def test_missing_year_not_guessed(self):
        e=extraer_texto('Aruba\n10 al 17 de enero\n4 pasajeros\nViaje para toda la familia con puntos Santander')
        self.assertNotIn('fecha_viaje',e.campos)
        self.assertNotIn('menores',e.campos)
        self.assertNotIn('puntos',e.campos)

if __name__=='__main__':unittest.main()
