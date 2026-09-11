from datetime import date
from app.services.date_utils import calcular_proxima_fecha, dias_restantes

def test_devuelve_este_mes_si_el_dia_no_ha_llegado():
    #Preparar: hoy es 10 de septiembre y el pago es el dia 12.
    hoy = date(2026, 9, 10)
    
    # Ejecutar: le pasamos la fecha en vez de dejar que mire el reloj,
    # así el test da el mismo resultado hoy, mañana y dentro de un año.
    resultado = calcular_proxima_fecha(dia_mes=12, hoy=hoy)
    
    # Comprobar: el día 12 todavía no pasó, así que toca este mismo mes.
    assert resultado == date(2026, 9, 12)
    
def test_salta_al_mes_siguiente_si_el_dia_ya_paso():
    #Preparar: hoy es 20 de septiembre y el pago es el dia 8.
    hoy = date(2026, 9, 20)
    
    # Ejecutar: le pasamos la fecha en vez de dejar que mire el reloj,
    # así el test da el mismo resultado hoy, mañana y dentro de un año.
    resultado = calcular_proxima_fecha(dia_mes=8, hoy=hoy)
    
    # Comprobar: el día 8 ya pasó, así que toca el mes siguiente.
    assert resultado == date(2026, 10, 8)
    
def test_devuelve_mismo_mes_si_el_dia_es_hoy():
    #Preparar: hoy es 12 de septiembre y el pago es el dia 12.
    hoy = date(2026, 9, 12)
    
    # Ejecutar: le pasamos la fecha en vez de dejar que mire el reloj,
    # así el test da el mismo resultado hoy, mañana y dentro de un año.
    resultado = calcular_proxima_fecha(dia_mes=12, hoy=hoy)
    
    # Comprobar: el día 12 es hoy, así que toca este mismo mes.
    assert resultado == date(2026, 9, 12)
    
def test_salto_de_mes_entre_diciembre_y_enero():
    #Preparar: hoy es 20 de diciembre y el pago es el dia 12.
    hoy = date(2026, 12, 20)
    
    # Ejecutar: le pasamos la fecha en vez de dejar que mire el reloj,
    # así el test da el mismo resultado hoy, mañana y dentro de un año.
    resultado = calcular_proxima_fecha(dia_mes=12, hoy=hoy)
    
    # Comprobar: el día 12 ya pasó, así que toca el mes siguiente (enero del año siguiente).
    assert resultado == date(2027, 1, 12)
    
def test_cambio_de_fecha_si_el_dia_no_existe():
    #Preparar: hoy es 1 de febrero de año bisiesto y el pago es el dia 31.
    hoy = date(2028, 2, 1)
    
    # Ejecutar: le pasamos la fecha en vez de dejar que mire el reloj,
    # así el test da el mismo resultado hoy, mañana y dentro de un año.
    resultado = calcular_proxima_fecha(dia_mes=31, hoy=hoy)
    
    # Comprobar: el día 31 ya pasó, así que toca el mes siguiente (marzo).
    assert resultado == date(2028, 2, 29)  # 2028 es bisiesto, así que febrero tiene 29 días.
    
def test_ajusta_al_ultimo_dia_cuando_el_mes_es_mas_corto():
    # Septiembre tiene 30 días, así que un pago fijado el 31 no existe ese mes.
    hoy = date(2026, 9, 1)

    resultado = calcular_proxima_fecha(dia_mes=31, hoy=hoy)

    # La regla es cobrar el último día disponible, no saltar al mes siguiente.
    # Eso lo decide _dia_efectivo con el min().
    assert resultado == date(2026, 9, 30)
    
def test_cuenta_los_dias_que_faltan_para_el_proximo_pago():
    hoy = date(2026, 9, 10)

    resultado = dias_restantes(dia_mes=12, hoy=hoy)

    # Del 10 al 12 hay 2 días. Restar dos fechas en Python da un timedelta,
    # y .days saca el número entero de días.
    assert resultado == 2