import pandas as pd
import calendar
import cod
import creds

FILE_CPI1913 = creds.cpi_script['FILE_CPI1913']

def get_cpi() -> pd.DataFrame:
    """
    Devuelve el IPC del archivo CPI1913.xlsx, con el CPI base 1967.
    :return: df 'CPI', 'InflaMensual', 'CantD'
    """
    cpi = pd.read_excel(FILE_CPI1913)[['Fecha', 'CPI']].copy() # TODO hacer el parse de la fecha acá.
    cpi['Fecha'] = pd.to_datetime(cpi['Fecha'], format='%Y-%m-%d')
    cpi['InflaMensual'] = cpi['CPI'].pct_change()
    cpi = cod.get_date(cpi, day=False)
    cpi['CantD'] = cpi.apply(lambda row: calendar.monthrange(row['Año'], row['Mes'])[1], axis=1)
    return cpi[cod.COLS[:-1] + ['CPI', 'InflaMensual', 'CantD']].copy()


def get_act_cap(df: pd.DataFrame, us: bool = False) -> pd.DataFrame:
    """
    Devuelve un df con datos diarios, para actualizar y capitalizar valores.
    :param us: Si agregar 'us' al final de las columnas del df o no.
    :param df: Datos con 'CPI', 'InflaMensual', 'Dia', 'CantD'.
    :return: df: 'Actualizador', 'Capitalizador'.
    """
    infla_column = 'InflaMensualUS' if us else 'InflaMensual'
    df['CPI'] = df['CPI'] / (1 + df[infla_column])
    df['CPI'] = df['CPI'] / df['CPI'].iloc[0]

    actualizador_column = 'ActualizadorUS' if us else 'Actualizador'
    capitalizador_column = 'CapitalizadorUS' if us else 'Capitalizador'

    df[actualizador_column] = df['CPI'] * (1 + df[infla_column]) ** (df['Dia'] / df['CantD'])
    df[capitalizador_column] = 1 / df[actualizador_column]
    df[capitalizador_column] = df[capitalizador_column] / df[capitalizador_column].iloc[-1]

    return df
