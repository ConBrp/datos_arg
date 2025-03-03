import pandas as pd
import calendar
import cod
import creds

FILE_INDEC_DIVISIONES = creds.ipc_script['FILE_INDEC_DIVISIONES']
URL_INDEC_DIVISIONES = 'https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv'
FILE_INDEC_APERTURAS = creds.ipc_script['FILE_INDEC_APERTURAS']
URL_INDEC_APERTURAS = 'https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_aperturas.csv'
FILE_INFLA_EMPALMADA = creds.ipc_script['FILE_INFLA_EMPALMADA']


def get_infla() -> (tuple[str, str], tuple[int, int]):
    """
    Devuelve los meses estimados en el archivo IPC2000.xlsx.
    :return: (mes, mes), (est, est)
    """
    return creds.ipc_script['INFLA_ESTIMADA']


def get_file_indec(tipo: int = 1) -> pd.DataFrame|None:
    """
    Devuelve un df del tipo seleccionado:
        1. Default: Archivo serie_ipc_divisiones.
        2. Archivo serie_ipc_aperturas.
    :param tipo: Tipo a seleccionar.
    :return: df con datos de la hoja seleccionada.
    """
    match tipo:
        case 1:
            return pd.read_csv(URL_INDEC_DIVISIONES, encoding='ISO-8859-1', decimal=",", delimiter=";")
            # return pd.read_csv(FILE_INDEC_DIVISIONES, encoding='ISO-8859-1', decimal=",", delimiter=";")
        case 2:
            return pd.read_csv(URL_INDEC_APERTURAS, encoding='ISO-8859-1', decimal=",", delimiter=";")
            # return pd.read_csv(FILE_INDEC_APERTURAS, encoding='ISO-8859-1', decimal=",", delimiter=";")
        case _:
            print(f'Error en get_file_INDEC(tipo: int = {tipo})')


def get_ipc() -> pd.DataFrame:
    """
    Devuelve un df con datos mensuales del IPC, del archivo IPC2000.xlsx.
    :return: df 'Fecha', 'Date', 'IPC', 'InflaMensual', 'CantD'
    """
    ipc = pd.read_excel(FILE_INFLA_EMPALMADA)
    ipc['Fecha'] = pd.to_datetime(ipc['Fecha'], format='%Y-%m-%d')
    ipc = ipc.set_index('Fecha', drop=False)
    ipc['InflaMensual'] = ipc['IPC'].pct_change()
    ipc = cod.get_date(ipc, day=False)
    ipc['CantD'] = ipc.apply(lambda row: calendar.monthrange(row['Año'], row['Mes'])[1], axis=1)
    return ipc[cod.COLS[:-1] + ['IPC', 'InflaMensual', 'CantD']].copy() # TODO ver si hace falta la columna 'Fecha', si ya está en el índice.


def get_act_cap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve un df con datos diarios, para actualizar y capitalizar valores.
    :param df: Datos con 'IPC', 'InflaMensual', 'Dia', 'CantD'.
    :return: df: 'Actualizador', 'Capitalizador'.
    """
    df['IPC'] = df['IPC'] / (1 + df['InflaMensual'])
    df['IPC'] = df['IPC'] / df['IPC'].iloc[0]
    df['Actualizador'] = df['IPC'] * (1 + df['InflaMensual']) ** (df['Dia'] / df['CantD'])

    df['Capitalizador'] = (1 / df['Actualizador'])

    df['Capitalizador'] = df['Capitalizador'] / df['Capitalizador'].iloc[-1]
    return df


def get_ipc_indec() -> pd.DataFrame:
    """
    Devuelve un df con datos mensuales del IPC, del archivo del INDEC.
    :return: df 'IPC', 'VarMoM', 'VarYoY', 'InflaMensual', 'Date'
    """
    df = get_file_indec()
    nacional = df.query("Codigo == '0' & Region == 'Nacional'")[['Periodo', 'Indice_IPC', 'v_m_IPC', 'v_i_a_IPC']].copy().reset_index(drop=True)
    nacional = nacional.apply(pd.to_numeric, errors='coerce')
    nacional['InflaMensual'] = nacional['Indice_IPC'].pct_change() * 100
    nacional["Date"] = pd.to_datetime(nacional['Periodo'], format='%Y%m').dt.strftime('%m-%Y')
    nacional = nacional[['Indice_IPC', 'v_m_IPC', 'v_i_a_IPC', 'InflaMensual', 'Date']].copy()
    nacional.columns = ['IPC', 'VarMoM', 'VarYoY', 'InflaMensual', 'Date']
    return nacional


def get_div_ipc(tipo: int = 1) -> pd.DataFrame:
    """
    Devuelve un df del tipo seleccionado:
        1. Default: Las 12 divisiones COICOP y el nivel general.
        2. Categorías: estacional, núcleo y regulados.
        3. Bienes y Servicios: B y S.
    :param tipo: Tipo a seleccionar.
    :return: df 'Codigo', 'Descripcion', 'Indice_IPC', 'Date' (Con día)
    """
    general = get_file_indec()
    columnas = ['Codigo', 'Descripcion', 'Periodo', 'Indice_IPC']
    match tipo:
        case 1:
            nacional = general.query("Region == 'Nacional' & Clasificador == 'Nivel general y divisiones COICOP'")[columnas].copy().reset_index(drop=1)
        case 2:
            nacional = general.query("Region == 'Nacional' & Clasificador == 'Categorias'")[columnas].copy().reset_index(drop=1)
            nacional['Descripcion'] = nacional['Codigo'].copy()
        case 3:
            nacional = general.query("Region == 'Nacional' & Clasificador == 'Bienes y servicios'")[columnas].copy().reset_index(drop=1)
            nacional['Descripcion'] = nacional['Codigo'].apply(
                lambda x: 'Bienes' if x == 'B' else ('Servicios' if x == 'S' else 'Other'))
        case _:
            nacional = None
            print('Error en get_div_IPC(tipo: int = 1)')

    nacional['Indice_IPC'] = pd.to_numeric(nacional['Indice_IPC'], errors='coerce')
    nacional = cod.get_date_ipc(nacional)
    return nacional[['Codigo', 'Descripcion', 'Indice_IPC', 'Date']].copy()


def get_aper_ipc(prepagas: bool = True) -> pd.DataFrame:
    """
    Devuelve un df con las aperturas del IPC.
    :param prepagas: Si corrige el código de prepagas o no.
    :return: df "Codigo", "Periodo", "Indice_IPC", "Region".
    """
    aperturas = get_file_indec(2)
    aperturas['Codigo'] = aperturas['Codigo'].astype(str)
    if prepagas:
        aperturas.loc[aperturas['Codigo'] == '06.4.1', 'Codigo'] = '06.4'
    aperturas['Indice_IPC'] = pd.to_numeric(aperturas['Indice_IPC'], errors='coerce')
    return aperturas[['Codigo', 'Descripcion_aperturas', 'Periodo', 'Indice_IPC', 'Region']].copy()


def get_ponderadores_ipc() -> pd.DataFrame:
    """
    Devuelve los ponderadores para las categorías según regiones, del IPC del archivo ponderadores_ipc.xls.
    :return: df 'Codigo', 'Descripcion', 'GBA', 'Pampeana', 'Noreste', 'Noroeste', 'Cuyo', 'Patagonia'.
    """
    ponderadores = pd.read_excel(r'C:\Users\berge\Desktop\Me\programs\1X\Data\ponderadores_ipc.xls', header=2).iloc[:-2, :].copy()
    ponderadores.columns = ['Codigo', 'Descripcion', 'GBA', 'Pampeana', 'Noreste', 'Noroeste', 'Cuyo', 'Patagonia']
    ponderadores['Codigo'] = ponderadores['Codigo'].astype(str)
    return ponderadores

