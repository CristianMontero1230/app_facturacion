# ===================== INSTALACIÓN DE LIBRERÍAS =====================

import gradio as gr
import pandas as pd
import plotly.express as px
import os
import json
import re
import streamlit as st
from datetime import datetime

print("=== INICIANDO IPS GOLEMAN APP - VERSIÓN CONSOLIDADA V2 ===")

# ===================== FORMATOS =====================
def formato_pesos(x):
    try:
        return "$ {:,.0f}".format(x).replace(",", ".")
    except:
        return x

def formato_cedula(x):
    try:
        return "Cédula: {:,.0f}".format(x).replace(",", ".")
    except:
        return x

def formato_edad(x):
    try:
        return f"{int(x)} años"
    except:
        return x

# ===================== FUNCIONES PARA GUARDAR META Y ESTADO =====================
STATE_FILE = "user_state.json"

def guardar_estado_filtros(prof, proc, ciudad, f_ini, f_fin):
    try:
        estado = {
            "profesional": prof,
            "procedimiento": proc,
            "ciudad": ciudad,
            "fecha_inicio": str(f_ini) if f_ini else None,
            "fecha_fin": str(f_fin) if f_fin else None
        }
        with open(STATE_FILE, "w") as f:
            json.dump(estado, f)
    except Exception as e:
        print(f"Error guardando estado: {e}")

def cargar_estado_filtros():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def guardar_meta(nombre_archivo, valor):
    with open(nombre_archivo, "w") as f:
        f.write(str(valor))

def cargar_meta(nombre_archivo):
    if os.path.exists(nombre_archivo):
        with open(nombre_archivo, "r") as f:
            try:
                return float(f.read().strip())
            except:
                return 0
    return 0

# ===================== PERSISTENCIA FECHA ACTUALIZACIÓN =====================
ARCHIVO_FECHA = "fecha_update.txt"

def guardar_fecha_actualizacion():
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(ARCHIVO_FECHA, "w") as f:
        f.write(now)
    return now

def cargar_fecha_actualizacion():
    if os.path.exists(ARCHIVO_FECHA):
        with open(ARCHIVO_FECHA, "r") as f:
            return f.read().strip()
    return "Sin actualizaciones"

# ===================== FUNCIONES PARA GUARDAR / CARGAR EXCEL =====================
def guardar_excel(df, nombre_archivo="base_guardada.xlsx"):
    df.to_excel(nombre_archivo, index=False)

def cargar_excel(nombre_archivo="base_guardada.xlsx"):
    if os.path.exists(nombre_archivo):
        try:
            return pd.read_excel(nombre_archivo)
        except:
            return None
    return None

# ===================== VARIABLES GLOBALES =====================
USUARIOS_VALIDOS = {"admin": "123", "cristian": "123"}
global_usuario = None
global_df = cargar_excel()
global_consolidado_path = None

# ===================== LOGIN =====================
def login(usuario, password):
    global global_usuario
    if USUARIOS_VALIDOS.get(usuario) == password:
        global_usuario = usuario
        notif = ""
        
        # Badge de usuario
        user_badge_html = f"""
        <div style='display:flex;align-items:center;gap:10px;background:#f1f5f9;padding:8px 16px;border-radius:20px;border:1px solid #cbd5e1;'>
            <div style='width:12px;height:12px;background:#10b981;border-radius:50%;'></div>
            <span style='color:#334155;font-weight:600;font-size:14px;'>👤 {global_usuario}</span>
        </div>
        """
        user_badge_update = gr.update(visible=True, value=user_badge_html)

        # Validar si es admin para mostrar/ocultar carga de archivo y editar meta
        is_admin = (usuario == "admin")
        
        # Cargar meta actual para asegurar que se muestre el valor persistente
        current_meta = cargar_meta("meta_dashboard.txt")
        
        archivo_update = gr.update(visible=True) if is_admin else gr.update(visible=False)
        meta_update = gr.update(interactive=True, value=current_meta) if is_admin else gr.update(interactive=False, value=current_meta)
        
        # Check consolidado visibility
        consol_val = None
        consol_vis = False
        if is_admin and os.path.exists("archivo_consolidado.xlsx"):
             consol_vis = True
             consol_val = "archivo_consolidado.xlsx"
        consol_update = gr.update(visible=consol_vis, value=consol_val)
        
        return gr.update(visible=False), gr.update(visible=True), "", notif, archivo_update, archivo_update, meta_update, user_badge_update, consol_update
    
    return gr.update(visible=True), gr.update(visible=False), "<div style='color:red; text-align:center; font-weight:bold'>❌ Usuario o contraseña incorrectos</div>", "", gr.update(), gr.update(), gr.update(), gr.update(visible=False), gr.update(visible=False)

def cerrar_sesion():
    global global_usuario
    nombre = global_usuario
    global_usuario = None
    notif = ""
    return (
        gr.update(visible=True), 
        gr.update(visible=False), 
        notif, 
        gr.update(value=None), # Prof
        gr.update(value=None), # Proc
        gr.update(value=None), # Ciudad
        gr.update(value=None), # Ini
        gr.update(value=None), # Fin
        gr.update(visible=False, value="") # User Badge
    )

# ===================== CARGA OPTIMIZADA DE EXCEL =====================

def find_col(df, candidates):
    for col in df.columns:
        if any(cand.lower() in str(col).lower() for cand in candidates):
            return col
    return None

def leer_excel(file_obj1, file_obj2=None):
    global global_df, global_consolidado_path
    
    # Obtener rutas de archivos (si son objetos de archivo de Gradio o strings)
    path1 = file_obj1.name if hasattr(file_obj1, 'name') else file_obj1
    path2 = file_obj2.name if hasattr(file_obj2, 'name') else file_obj2

    global_consolidado_path = None
    
    # Caso 1: No hay archivos nuevos -> Cargar memoria o disco
    if file_obj1 is None and file_obj2 is None:
        if global_df is not None:
            return global_df
        return cargar_excel()

    try:
        df1 = pd.DataFrame()
        df2 = pd.DataFrame()

        # Cargar archivo 1
        if file_obj1 is not None:
            df1 = pd.read_excel(file_obj1, engine="openpyxl")
        
        # Cargar archivo 2
        if file_obj2 is not None:
            df2 = pd.read_excel(file_obj2, engine="openpyxl")

        # --- LIMPIEZA PRELIMINAR DE PROFESIONAL EN DF1 (Para filtros y visualización) ---
        col_prof1 = find_col(df1, ["profesional", "nombre profesional"])
        if col_prof1:
             # Eliminar números al inicio (ej: "123 - JUAN" -> "JUAN")
             df1[col_prof1] = df1[col_prof1].astype(str).str.replace(r'^\d+\s*[-]?\s*', '', regex=True).str.strip()

        # Lógica de unión / consolidación
        if not df1.empty and not df2.empty:
            # Intentar consolidación
            col_code1 = find_col(df1, ["codigo procedimiento", "cod procedimiento", "codigo", "cups"])
            col_code2 = find_col(df2, ["codigo procedimiento", "cod procedimiento", "codigo", "cups"])
            
            col_name1 = find_col(df1, ["nombre procedimiento", "procedimiento", "descripcion", "nombre"])
            col_name2 = find_col(df2, ["nombre procedimiento", "procedimiento", "descripcion", "nombre"])
            
            col_val_unit2 = find_col(df2, ["valor unitario", "valor_unitario", "precio", "valor"])

            if col_val_unit2 and (col_code1 and col_code2 or col_name1 and col_name2):
                print(f"Consolidando archivos con búsqueda inteligente...")
                
                # --- PREPARAR CLAVES TEMPORALES (Para no afectar formato original) ---
                if col_code1: df1['_temp_code'] = df1[col_code1].astype(str).str.strip()
                if col_code2: df2['_temp_code'] = df2[col_code2].astype(str).str.strip()
                
                if col_name1: df1['_temp_name'] = df1[col_name1].astype(str).str.strip().str.lower()
                if col_name2: df2['_temp_name'] = df2[col_name2].astype(str).str.strip().str.lower()
                
                # Inicializar columna temporal para el valor encontrado
                df1['__Valor_Encontrado__'] = None
                
                # 1. BÚSQUEDA POR CÓDIGO (Prioridad Alta)
                if col_code1 and col_code2:
                    # Crear mapa: Codigo -> Valor Unitario
                    # Asegurar que tomamos valores válidos del archivo 2
                    df2_clean = df2.dropna(subset=[col_val_unit2])
                    # Remover duplicados en código para evitar errores
                    df2_unique = df2_clean.drop_duplicates(subset=['_temp_code'])
                    price_map_code = df2_unique.set_index('_temp_code')[col_val_unit2].to_dict()
                    
                    df1['__Valor_Encontrado__'] = df1['_temp_code'].map(price_map_code)
                    print(f"DEBUG: Coincidencias encontradas por CÓDIGO: {df1['__Valor_Encontrado__'].notna().sum()}")
                
                # 2. BÚSQUEDA POR NOMBRE (Prioridad Baja - Rellenar huecos)
                if col_name1 and col_name2:
                    df2_clean = df2.dropna(subset=[col_val_unit2])
                    df2_unique = df2_clean.drop_duplicates(subset=['_temp_name'])
                    price_map_name = df2_unique.set_index('_temp_name')[col_val_unit2].to_dict()
                    
                    # Solo rellenar donde NO se encontró por código (donde es NaN)
                    mask_missing = df1['__Valor_Encontrado__'].isna()
                    df1.loc[mask_missing, '__Valor_Encontrado__'] = df1.loc[mask_missing, '_temp_name'].map(price_map_name)
                    print(f"DEBUG: Coincidencias totales tras búsqueda por NOMBRE: {df1['__Valor_Encontrado__'].notna().sum()}")
                
                # --- ACTUALIZAR COLUMNAS EN DF1 ---
                
                # 1. Valor Unitario
                col_val_unit1 = find_col(df1, ["valor unitario", "valor_unitario", "precio unitario"])
                if not col_val_unit1:
                     col_val_unit1 = "Valor Unitario"
                     if col_val_unit1 not in df1.columns:
                        df1[col_val_unit1] = 0.0
                
                # Preparar valores
                vals_nuevos = pd.to_numeric(df1['__Valor_Encontrado__'], errors='coerce')
                vals_actuales = pd.to_numeric(df1[col_val_unit1], errors='coerce').fillna(0)
                
                # Actualizar: Priorizar valor encontrado en Archivo 2; si no, mantener original
                df1[col_val_unit1] = vals_nuevos.combine_first(vals_actuales)
                
                # 2. Cantidad
                col_qty1 = find_col(df1, ["cantidad", "cant"])
                if col_qty1:
                    qtys = pd.to_numeric(df1[col_qty1], errors='coerce').fillna(1)
                else:
                    qtys = 1
                
                # 3. Valor (Total) - Requerimiento: "adjuntalos en el archivo 1 en la celda valor"
                col_total1 = find_col(df1, ["valor total", "total", "valor neto", "neto", "valor"])
                if not col_total1:
                    col_total1 = "Valor" # Crear columna Valor si no existe
                
                # Calcular Total: Unitario (actualizado) * Cantidad
                val_unit_safe = pd.to_numeric(df1[col_val_unit1], errors='coerce').fillna(0)
                
                # qtys ya está limpio desde el paso 2
                
                # Verificar si 'Valor' es el total esperado o unitario.
                # Asumimos que si existe Valor Unitario y Cantidad, 'Valor' es el Total.
                df1[col_total1] = val_unit_safe * qtys
                
                # Limpiar columnas temporales
                for tmp in ['_temp_code', '_temp_name', '__Valor_Encontrado__']:
                    if tmp in df1.columns:
                        df1.drop(columns=[tmp], inplace=True)
                
                df = df1
            
                # --- LIMPIEZA Y GUARDADO SEGURO DEL CONSOLIDADO ---
                try:
                    print(f"DEBUG: Iniciando limpieza de datos para exportación. Filas: {len(df)}")
                    
                    # 0. LIMPIEZA DE ARCHIVOS ANTIGUOS (SOLICITUD USUARIO)
                    # Eliminar todos los consolidados previos para no llenar la carpeta
                    try:
                        import glob
                        consolidados_viejos = glob.glob("archivo_consolidado*.xlsx")
                        for f_old in consolidados_viejos:
                            try:
                                os.remove(f_old)
                                print(f"DEBUG: Eliminado archivo antiguo: {f_old}")
                            except Exception as e_del:
                                print(f"DEBUG: No se pudo eliminar {f_old} (posiblemente abierto): {e_del}")
                    except Exception as e_glob:
                        print(f"Error limpiando archivos viejos: {e_glob}")

                    # 1. Eliminar columna auxiliar si existe
                    if 'Valor_Unitario_Ref' in df.columns:
                        df = df.drop(columns=['Valor_Unitario_Ref'])
                    
                    df_export = df.copy()
                    
                    # 2. Eliminar columnas duplicadas
                    df_export = df_export.loc[:, ~df_export.columns.duplicated()]

                    # 2.1 Normalizar nombres de columnas
                    df_export.columns = df_export.columns.astype(str).str.strip()

                    # 3. Limpieza profunda de datos por columna
                    for col in df_export.columns:
                        col_lower = col.lower()
                        
                        # 3.1 Manejo de Fechas (SOLICITUD: FECHA CORTA)
                        if "fecha" in col_lower or "inicio" in col_lower or "fin" in col_lower or pd.api.types.is_datetime64_any_dtype(df_export[col]):
                            try:
                                # Convertir a datetime primero para asegurar (Soporte mixed para robustez)
                                df_export[col] = pd.to_datetime(df_export[col], errors='coerce', dayfirst=True, format='mixed')
                                # Formatear a fecha corta string (DD/MM/YYYY)
                                # Esto asegura que en el Excel se vea "corta" y limpia la hora
                                df_export[col] = df_export[col].dt.strftime('%d/%m/%Y')
                                # Reemplazar NaT con vacío
                                df_export[col] = df_export[col].fillna("")
                            except Exception as e_date:
                                print(f"DEBUG: Error limpiando fecha en {col}: {e_date}")
                                df_export[col] = df_export[col].astype(str)
                        
                        # 3.1.5 Manejo de Profesional (SOLICITUD: Solo nombre)
                        elif "profesional" in col_lower:
                            # Regex para eliminar números iniciales y separadores (ej. "123 - JUAN" -> "JUAN")
                            try:
                                df_export[col] = df_export[col].astype(str).str.replace(r'^\d+\s*[-]?\s*', '', regex=True).str.strip()
                            except:
                                pass

                        # 3.2 Asegurar numéricos en columnas clave
                        elif col == col_val_unit1 or col == col_total1:
                             df_export[col] = pd.to_numeric(df_export[col], errors='coerce').fillna(0)
                        
                        # 3.3 Limpiar columnas de texto (Object)
                        elif df_export[col].dtype == 'object':
                            # Convertir a string explícito, reemplazando NaN con vacío
                            df_export[col] = df_export[col].fillna("").astype(str)
                            
                            # Eliminar caracteres de control inválidos para XML
                            # Rango permitido: \x09 (tab), \x0A (LF), \x0D (CR), y >= \x20
                            df_export[col] = df_export[col].apply(lambda x: re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', x))
                            
                            # Evitar inyección de fórmulas
                            df_export[col] = df_export[col].apply(lambda x: "'" + x if str(x).startswith("=") else x)
                            
                            # Truncar a límite de celda de Excel (32767 caracteres)
                            df_export[col] = df_export[col].str.slice(0, 32700)

                    # 5. Guardar usando xlsxwriter (Motor más robusto para escritura)
                    output_path = os.path.abspath("archivo_consolidado.xlsx")
                    print(f"DEBUG: Intentando guardar en: {output_path}")
                    
                    # Eliminar archivo previo si existe para evitar bloqueos
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except Exception as e_rm:
                            print(f"DEBUG: No se pudo eliminar archivo previo (posiblemente abierto): {e_rm}")
                            # Intentar con nombre alternativo si falla
                            output_path = os.path.abspath(f"archivo_consolidado_{int(datetime.now().timestamp())}.xlsx")
                            print(f"DEBUG: Usando nombre alternativo: {output_path}")

                    try:
                        import xlsxwriter
                        # Usar xlsxwriter con opciones para manejar errores de datos
                        with pd.ExcelWriter(output_path, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
                             df_export.to_excel(writer, index=False)
                        print("DEBUG: Guardado exitoso con xlsxwriter")
                    except Exception as e_xlsx:
                        print(f"DEBUG: Falló xlsxwriter ({e_xlsx}). Intentando openpyxl...")
                        df_export.to_excel(output_path, index=False, engine='openpyxl')
                        print("DEBUG: Guardado exitoso con openpyxl")
                    
                    # Actualizar variable global si cambió el nombre
                    if "archivo_consolidado.xlsx" not in output_path:
                        # Si tuvimos que cambiar el nombre, intentar renombrar o copiar al original si es posible,
                        # o actualizar la referencia para la descarga.
                        # Por simplicidad en esta estructura, intentamos copiar de vuelta si se libera.
                        try:
                            import shutil
                            shutil.copy(output_path, "archivo_consolidado.xlsx")
                        except:
                            pass # Si sigue bloqueado, el usuario descargará el anterior o fallará, pero el proceso terminó.

                    # 6. Verificación de integridad final
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                         global_consolidado_path = output_path
                         print(f"Archivo consolidado generado y verificado: {global_consolidado_path}")
                    else:
                         print("ADVERTENCIA: El archivo consolidado tiene 0 bytes o no existe.")

                except Exception as e_save:
                    print(f"ERROR CRÍTICO guardando consolidado: {e_save}")
                    import traceback
                    traceback.print_exc()

            
            else:
                print("No se encontraron columnas para consolidar. Concatenando...")
                df = pd.concat([df1, df2], ignore_index=True)

        elif not df1.empty:
            df = df1
        elif not df2.empty:
            df = df2
        else:
            return global_df or cargar_excel()

        # Limpieza básica
        df.columns = df.columns.astype(str).str.strip()
        
        global_df = df
        guardar_excel(df)
        
        # Actualizar fecha y hora
        guardar_fecha_actualizacion()
        
        return df
    except Exception as e:
        print(f"Error leyendo archivos: {e}")
        return global_df

# ===================== FORMATEO Y TOTALES =====================
def formatear_df(df):
    df_format = df.copy()
    for col in df_format.columns:
        if col.lower() == "valor":
            df_format[col] = df_format[col].apply(formato_pesos)
        elif col.lower() == "identificacion":
            df_format[col] = df_format[col].apply(formato_cedula)
        elif col.lower() == "edad":
            df_format[col] = df_format[col].apply(formato_edad)
    return df_format

def calcular_totales(df):
    col_valor = next((c for c in df.columns if str(c).strip().lower() == "valor"), None)
    if col_valor:
        serie = pd.to_numeric(df[col_valor], errors="coerce")
        serie = serie[serie > 0]
        total_valor = serie.sum(skipna=True)
        return pd.DataFrame({"TOTAL VALOR": [formato_pesos(total_valor)]})
    return pd.DataFrame({"TOTAL VALOR": ["❌ No existe columna 'valor'"]})

def calcular_totales_por_procedimiento(df):
    if df is None or df.empty:
        return pd.DataFrame()
    col_proc = next((c for c in df.columns if str(c).strip().lower() == "nombre procedimiento"), None)
    if not col_proc:
        col_proc = next((c for c in df.columns if "nombre procedimiento" in str(c).lower()), None)
    col_valor = next((c for c in df.columns if str(c).strip().lower() == "valor"), None)
    if not col_valor:
        col_valor = next((c for c in df.columns if "valor" in str(c).lower()), None)
    if not col_proc or not col_valor:
        return pd.DataFrame()

    # Fix for duplicate columns
    series_proc = df[col_proc]
    if isinstance(series_proc, pd.DataFrame):
        series_proc = series_proc.iloc[:, 0]
    
    series_val = df[col_valor]
    if isinstance(series_val, pd.DataFrame):
        series_val = series_val.iloc[:, 0]

    temp = pd.DataFrame({
        col_proc: series_proc,
        col_valor: series_val
    })

    temp["_valor_num"] = pd.to_numeric(temp[col_valor], errors="coerce")
    temp = temp[temp["_valor_num"] > 0]
    
    # Normalizar nombre procedimiento para agrupación correcta
    temp[col_proc] = temp[col_proc].astype(str).str.strip().str.upper()
    
    agrupado = temp.groupby(col_proc, dropna=False)["_valor_num"].sum().reset_index(name="Valor_Total")
    agrupado = agrupado.sort_values(by="Valor_Total", ascending=False).reset_index(drop=True)
    agrupado["Valor_Total"] = agrupado["Valor_Total"].apply(formato_pesos)
    return agrupado
def calcular_totales_por_procedimiento_numerico(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["Procedimiento", "Valor_Total_Num"])
    col_proc = next((c for c in df.columns if str(c).strip().lower() == "nombre procedimiento"), None)
    if not col_proc:
        col_proc = next((c for c in df.columns if "nombre procedimiento" in str(c).lower()), None)
    col_valor = next((c for c in df.columns if str(c).strip().lower() == "valor"), None)
    if not col_valor:
        col_valor = next((c for c in df.columns if "valor" in str(c).lower()), None)
    if not col_proc or not col_valor:
        return pd.DataFrame(columns=["Procedimiento", "Valor_Total_Num"])
    
    # Fix for duplicate columns
    series_proc = df[col_proc]
    if isinstance(series_proc, pd.DataFrame):
        series_proc = series_proc.iloc[:, 0]
    
    series_val = df[col_valor]
    if isinstance(series_val, pd.DataFrame):
        series_val = series_val.iloc[:, 0]

    temp = pd.DataFrame({
        col_proc: series_proc,
        col_valor: series_val
    })

    temp["_valor_num"] = pd.to_numeric(temp[col_valor], errors="coerce")
    temp = temp[temp["_valor_num"] > 0]
    
    # Normalizar nombre procedimiento para agrupación correcta
    temp[col_proc] = temp[col_proc].astype(str).str.strip().str.upper()
    
    agrupado = temp.groupby(col_proc, dropna=False)["_valor_num"].sum().reset_index()
    agrupado.columns = ["Procedimiento", "Valor_Total_Num"]
    return agrupado
# ===================== HELPER FUNCTIONS FOR DROPDOWNS =====================
def cargar_procedimientos(f1, f2):
    df = leer_excel(f1, f2)
    if df is None:
        return gr.update(choices=[])
    col_proc = next((c for c in df.columns if c.strip().lower() == "nombre procedimiento"), None)
    if not col_proc:
        col_proc = next((c for c in df.columns if "nombre procedimiento" in c.lower()), None)
    if col_proc:
        serie = df[col_proc]
        if isinstance(serie, pd.DataFrame):
            serie = serie.iloc[:, 0]
        serie = serie.astype(str).str.strip()
        mapa = {}
        for v in serie.dropna():
            k = v.lower()
            if k not in mapa:
                mapa[k] = v
        return gr.update(choices=sorted(mapa.values()))
    return gr.update(choices=[])

def cargar_profesionales(f1, f2):
    df = leer_excel(f1, f2)
    if df is None:
        return gr.update(choices=[])
    col_prof = next((c for c in df.columns if c.strip().lower() == "profesional"), None)
    if not col_prof:
        col_prof = next((c for c in df.columns if "profesional" in c.lower()), None)
    if col_prof:
        serie = df[col_prof]
        if isinstance(serie, pd.DataFrame):
            serie = serie.iloc[:, 0]
        serie = serie.astype(str).str.strip()
        mapa = {}
        for v in serie.dropna():
            k = v.lower()
            if k not in mapa:
                mapa[k] = v
        return gr.update(choices=sorted(mapa.values()))
    return gr.update(choices=[])

def cargar_ciudades(f1, f2):
    # Intentar cargar desde archivo consolidado si existe
    if os.path.exists("archivo_consolidado.xlsx"):
        try:
             df = pd.read_excel("archivo_consolidado.xlsx", engine="openpyxl")
        except:
             df = leer_excel(f1, f2)
    else:
        df = leer_excel(f1, f2)

    if df is None:
        return gr.update(choices=[])
    # Buscar columna ciudad
    col_ciudad = next((c for c in df.columns if "ciudad" in str(c).lower() or "municipio" in str(c).lower() or "sede" in str(c).lower()), None)
    
    # Si no encuentra en consolidado (posiblemente porque las columnas se limpiaron o cambiaron de nombre)
    if not col_ciudad:
         # Intento de búsqueda más agresiva
         for c in df.columns:
             if "muni" in str(c).lower() or "ciud" in str(c).lower():
                 col_ciudad = c
                 break
                 
    if col_ciudad:
        serie = df[col_ciudad]
        if isinstance(serie, pd.DataFrame):
            serie = serie.iloc[:, 0]
        serie = serie.astype(str).str.strip()
        mapa = {}
        for v in serie.dropna():
            k = v.lower()
            if k not in mapa:
                mapa[k] = v
        return gr.update(choices=sorted(mapa.values()))
    return gr.update(choices=[])

# ===================== FILTROS OPTIMIZADOS =====================
def filtrar_datos(df, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad):
    aviso = ""
    if df is None:
        return pd.DataFrame(), aviso

    df_filtrado = df.copy()

    # --- Filtro : profesional ---
    col_profesional = next((c for c in df.columns if str(c).strip().lower() == "profesional"), None)
    if not col_profesional:
        col_profesional = next((c for c in df.columns if "profesional" in str(c).lower()), None)
    if nombre_prof and col_profesional:
        nombre_prof_key = str(nombre_prof).strip().lower()
        comp = df_filtrado[col_profesional].astype(str).str.strip().str.lower()
        df_filtrado = df_filtrado[comp == nombre_prof_key]

    # --- Filtro : procedimiento ---
    col_procedimiento = next((c for c in df.columns if str(c).strip().lower() == "nombre procedimiento"), None)
    if not col_procedimiento:
         col_procedimiento = next((c for c in df.columns if "nombre procedimiento" in str(c).lower()), None)
    
    if procedimiento and col_procedimiento:
        procedimiento_key = str(procedimiento).strip().lower()
        compp = df_filtrado[col_procedimiento].astype(str).str.strip().str.lower()
        df_filtrado = df_filtrado[compp == procedimiento_key]
    
    # --- Filtro : ciudad ---
    col_ciudad = next((c for c in df.columns if "ciudad" in str(c).lower() or "municipio" in str(c).lower() or "sede" in str(c).lower()), None)
    if ciudad and col_ciudad:
        ciudad_key = str(ciudad).strip().lower()
        compc = df_filtrado[col_ciudad].astype(str).str.strip().str.lower()
        df_filtrado = df_filtrado[compc == ciudad_key]

    # --- Filtro por fechas (Rango) ---
    col_fecha = next((c for c in df.columns if str(c).strip().lower() == "fecha"), None)
    if not col_fecha:
        col_fecha = next((c for c in df.columns if "fecha" in str(c).lower()), None)

    if col_fecha:
        try:
            fechas_series = pd.to_datetime(df_filtrado[col_fecha], errors="coerce", dayfirst=True).dt.date
            mask = pd.Series(True, index=df_filtrado.index)

            if fecha_inicio:
                fi = pd.to_datetime(fecha_inicio).date()
                mask = mask & (fechas_series >= fi)
            
            if fecha_fin:
                ff = pd.to_datetime(fecha_fin).date()
                mask = mask & (fechas_series <= ff)
            
            df_filtrado = df_filtrado[mask]
                
        except Exception as e:
            aviso += f"⚠️ Error con fechas: {e}"
    else:
        aviso += "⚠️ No hay columna de fecha."
        
    return df_filtrado, aviso

def actualizar_analisis(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad):
    # Guardar estado actual de filtros para persistencia
    guardar_estado_filtros(nombre_prof, procedimiento, ciudad, fecha_inicio, fecha_fin)

    df = leer_excel(f1, f2)
    
    # Inicializar variables clave para evitar NameError
    col_procedimiento = None
    col_profesional = None
    col_paciente = None
    col_valor = None

    df_filtrado, aviso = filtrar_datos(df, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)

    if df_filtrado.empty and df is None:
        return pd.DataFrame(), "", pd.DataFrame(), aviso

    # --- Agregación Principal: Paciente x Procedimiento ---
    # Detectar columna paciente: PRIORIDAD A "nombre completo pacientes"
    col_paciente = next((c for c in df.columns if "nombre completo pacientes" in str(c).lower()), None)
    if not col_paciente:
         col_paciente = next((c for c in df.columns if "nombre completo paciente" in str(c).lower()), None)
    if not col_paciente:
        col_paciente = next((c for c in df.columns if "paciente" in str(c).lower()), None)
    if not col_paciente:
         col_paciente = next((c for c in df.columns if "usuario" in str(c).lower() or "nombre" in str(c).lower() and "procedimiento" not in str(c).lower() and "profesional" not in str(c).lower()), None)
    
    col_valor = next((c for c in df.columns if str(c).strip().lower() == "valor"), None)
    if not col_valor:
        col_valor = next((c for c in df.columns if "valor" in str(c).lower()), None)

    df_pacientes = pd.DataFrame()
    col_procedimiento = next((c for c in df.columns if str(c).strip().lower() == "nombre procedimiento"), None)
    if not col_procedimiento:
         col_procedimiento = next((c for c in df.columns if "nombre procedimiento" in str(c).lower()), None)

    col_profesional = next((c for c in df.columns if str(c).strip().lower() == "profesional"), None)
    if not col_profesional:
        col_profesional = next((c for c in df.columns if "profesional" in str(c).lower()), None)

    if col_paciente and col_procedimiento:
        try:
            temp_p = df_filtrado.copy()
            
            # Normalización de textos para agrupación exacta
            # Extracción segura de Series (evitando DataFrames por columnas duplicadas)
            series_paciente = temp_p[col_paciente]
            if isinstance(series_paciente, pd.DataFrame):
                series_paciente = series_paciente.iloc[:, 0]
            
            series_procedimiento = temp_p[col_procedimiento]
            if isinstance(series_procedimiento, pd.DataFrame):
                series_procedimiento = series_procedimiento.iloc[:, 0]

            # Extraer columna de valor para calcular total monetario por paciente
            series_valor = pd.Series([0]*len(series_paciente), index=temp_p.index)
            if col_valor:
                v = temp_p[col_valor]
                if isinstance(v, pd.DataFrame):
                    v = v.iloc[:, 0]
                series_valor = pd.to_numeric(v, errors="coerce").fillna(0)

            # Crear DataFrame limpio para evitar errores de columnas duplicadas en el grouper
            df_clean = pd.DataFrame({
                "Paciente_Clean": series_paciente.astype(str).str.strip().str.upper(),
                "Procedimiento_Clean": series_procedimiento.astype(str).str.strip().str.upper(),
                "Valor_Clean": series_valor.values
            })
            
            # Agrupar por Paciente y Procedimiento (PIVOT TABLE)
            # Filas: Paciente, Columnas: Procedimiento, Valores: Cantidad de servicios
            df_pivot = df_clean.pivot_table(
                index="Paciente_Clean", 
                columns="Procedimiento_Clean", 
                aggfunc='size', 
                fill_value=0
            )
            
            # Calcular Totales por paciente
            df_pivot["TOTAL SERVICIOS"] = df_pivot.sum(axis=1)
            
            # Calcular Total Monetario por paciente
            total_valor_por_paciente = df_clean.groupby("Paciente_Clean")["Valor_Clean"].sum()
            df_pivot["VALOR TOTAL"] = total_valor_por_paciente
            
            # Reordenar columnas: Mover TOTAL SERVICIOS y VALOR TOTAL al inicio
            cols = list(df_pivot.columns)
            # Remover los totales de la lista actual
            if "TOTAL SERVICIOS" in cols: cols.remove("TOTAL SERVICIOS")
            if "VALOR TOTAL" in cols: cols.remove("VALOR TOTAL")
            # Insertar al principio
            new_cols = ["TOTAL SERVICIOS", "VALOR TOTAL"] + cols
            df_pivot = df_pivot[new_cols]
            
            # Formatear VALOR TOTAL
            df_pivot["VALOR TOTAL"] = df_pivot["VALOR TOTAL"].apply(formato_pesos)

            # Resetear index para que Paciente sea una columna
            df_pacientes = df_pivot.reset_index()
            
            # Renombrar columna índice a algo legible
            df_pacientes.rename(columns={"Paciente_Clean": col_paciente}, inplace=True)
            
            # Ordenar por Total Servicios descendente
            df_pacientes = df_pacientes.sort_values(by="TOTAL SERVICIOS", ascending=False)
            
        except Exception as e:
            aviso += f" ⚠️ Error agrupando pacientes: {e}"
            df_pacientes = df_filtrado # Fallback a datos crudos si falla agrupación
            
    else:
        # Si no se detectan columnas clave, mostrar filtrado original pero avisar
        df_pacientes = df_filtrado
        if not col_paciente:
            aviso += " (No se detectó columna 'Nombre Completo Pacientes' o similar)"

    # --- Agregación Resumen: Profesional + Procedimiento (Inferior) ---
    resumen_df = pd.DataFrame()
    if col_profesional and col_procedimiento:
        try:
            temp = df_filtrado.copy()
            if col_valor:
                temp["_valor_num"] = pd.to_numeric(temp[col_valor], errors="coerce").fillna(0)
            else:
                temp["_valor_num"] = 0
            resumen_df = temp.groupby([col_profesional, col_procedimiento], dropna=False).agg(
                Servicios=("_valor_num", "size"),
                Valor_Total=("_valor_num", "sum")
            ).reset_index()
            resumen_df = resumen_df.sort_values(
                by=["Valor_Total", col_profesional, col_procedimiento],
                ascending=[False, True, True]
            ).reset_index(drop=True)
            for c in ["Valor_Total"]:
                resumen_df[c] = resumen_df[c].apply(formato_pesos)
        except Exception as e:
            aviso += f" ⚠️ Error en agregación resumen: {e}"
            resumen_df = pd.DataFrame()

    # Total filtrado (HTML)
    totales_df = calcular_totales(df_filtrado)
    valor_total = totales_df.iloc[0,0] if totales_df is not None else "❌"
    total_html = f"<div style='text-align:center; background:#e0fbfc; padding:16px; border-radius:12px;'><h3 style='color:#005f73;'>💰 Total filtrado: {valor_total}</h3></div>"
    
    # Retornamos df_pacientes como la tabla principal
    return df_pacientes, total_html, resumen_df, aviso


def render_resumen_html(resumen_df, titulo):
    if resumen_df is None or resumen_df.empty:
        return "<div style='background:#fff3cd;color:#856404;padding:12px;border-radius:10px;text-align:center;'>Sin datos para mostrar</div>"
    cols = list(resumen_df.columns)
    # Espera columnas: [Profesional, Nombre procedimiento, Servicios, Valor_Total]
    # Detecta nombres reales de columnas dinámicamente
    col_prof = next((c for c in cols if "profesional" in str(c).lower()), None)
    col_proc = next((c for c in cols if "procedimiento" in str(c).lower()), None)
    html = f"<div style='background:#f8fafc;padding:16px;border-radius:16px;'>"
    html += f"<h3 style='margin:0 0 12px 0;color:#0f766e'>{titulo}</h3>"
    html += "<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;'>"
    for _, r in resumen_df.head(12).iterrows():
        servicios = r.get("Servicios", "")
        vtotal = r.get("Valor_Total", "")
        prof = r.get(col_prof, "")
        proc = r.get(col_proc, "")
        html += f"""
        <div style='background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.06)'>
            <div style='font-weight:700;color:#334155'>{prof}</div>
            <div style='color:#475569'>{proc}</div>
            <div style='margin-top:8px;display:flex;gap:8px;flex-wrap:wrap'>
                <span style='background:#f1f5f9;border-radius:999px;padding:4px 8px'>Servicios: {servicios}</span>
                <span style='background:#dcfce7;border-radius:999px;padding:4px 8px'>Total: {vtotal}</span>
            </div>
        </div>
        """
    html += "</div></div>"
    return html

# ===================== DASHBOARD PROFESIONAL =====================
def generar_dashboard_profesional(df, meta_general):
    if df is None or df.empty:
        return "❌ Primero sube un archivo Excel.", "❌ Primero sube un archivo Excel."
    meta_global = float(meta_general) if meta_general else cargar_meta("meta_dashboard.txt")
    guardar_meta("meta_dashboard.txt", meta_global)
    col_prof = next((c for c in df.columns if "profesional" in str(c).lower()), None)
    col_proc = next((c for c in df.columns if "nombre procedimiento" in str(c).lower()), None)
    if not col_prof or not col_proc:
        return "❌ El archivo debe contener columnas Profesional y Nombre procedimiento.", ""
    df_counts = df.groupby([col_prof, col_proc]).size().reset_index(name="Conteo")
    df_totales = df_counts.groupby(col_prof)["Conteo"].sum().reset_index(name="Total_Profesional")
    df_totales = df_totales.sort_values(by="Total_Profesional", ascending=False).reset_index(drop=True)
    colores = ["#6a11cb", "#2575fc", "#f39c12", "#e74c3c", "#2ecc71", "#1abc9c", "#9b59b6", "#34495e"]
    mensaje_html = "<div style='background:#f8f9fa;padding:15px;border-radius:10px;'>"
    mensaje_html += f"<h3>📋 Servicios por Profesional</h3><b>Meta General: {meta_global}</b><br><br>"
    for i, row in df_totales.iterrows():
        total_p = row["Total_Profesional"]
        porcentaje = min((total_p / meta_global) * 100, 100) if meta_global > 0 else 0
        color_bar = colores[i % len(colores)]
        mensaje_html += f"""
        <div style='margin-bottom:18px;padding:12px;background:#ffffff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1);'>
            <div style='font-weight:700'>{row[col_prof]}</div>
            <div><b>Total Servicios:</b> {int(total_p)}</div>
            <div style='background:#ddd;border-radius:6px;width:100%;height:20px;margin-top:6px;'>
                <div style='background:{color_bar}; width:{porcentaje}%; height:100%; border-radius:6px;'></div>
            </div>
            <small>{porcentaje:.2f}% de la meta general</small>
            <div style='margin-top:10px;'>
        """
        sub = df_counts[df_counts[col_prof] == row[col_prof]].sort_values(by="Conteo", ascending=False)
        for j, srow in sub.iterrows():
            sub_pct = min((srow["Conteo"] / total_p) * 100, 100) if total_p > 0 else 0
            sub_color = colores[j % len(colores)]
            mensaje_html += f"""
                <div style='margin:6px 0;'>
                    <span>{srow[col_proc]}</span> — <b>{int(srow["Conteo"])}</b>
                    <div style='background:#eee;border-radius:6px;width:100%;height:14px;margin-top:4px;'>
                        <div style='background:{sub_color}; width:{sub_pct}%; height:100%; border-radius:6px;'></div>
                    </div>
                </div>
            """
        mensaje_html += "</div></div>"
    mensaje_html += "</div>"
    df_top10 = df_totales.head(10).reset_index(drop=True)
    ranking_html = "<div style='background:#fff3e0;padding:10px;border-radius:10px;'><h4>🏆 Ranking Top 10 Profesionales</h4>"
    for i, row in df_top10.iterrows():
        porcentaje = min((row['Total_Profesional'] / meta_global) * 100, 100) if meta_global > 0 else 0
        color_bar = colores[i % len(colores)]
        ranking_html += f"""
        <div style='margin-bottom:10px;'>
            <b>{row[col_prof]}</b> - Total: {int(row['Total_Profesional'])}<br>
            <div style='background:#ddd;border-radius:5px;width:100%;height:15px;margin-top:2px;'>
                <div style='width:{porcentaje}%;height:100%;background:{color_bar};border-radius:5px;'></div>
            </div>
            <small>{porcentaje:.2f}% de la meta</small>
        </div>
        """
    ranking_html += "</div>"
    return mensaje_html, ranking_html

# ===================== TAB CUMPLIMIENTO =====================
def calcular_cumplimiento_logic(total_actual, meta):
    porcentaje = min((total_actual / meta) * 100, 100) if meta > 0 else 0
    faltante = max(meta - total_actual, 0)

    mensaje = f"""
<div style='background:#e3f6ff;padding:20px;border-radius:10px;border-left:10px solid #0077b6'>
<h2>📊 Estado del Cumplimiento</h2>
<b>🎯 Meta establecida:</b> {formato_pesos(meta)}<br>
<b>💰 Total actual (Filtrado):</b> {formato_pesos(total_actual)}<br>
<b>📈 Porcentaje alcanzado:</b> <span style='color:green;font-size:22px'><b>{porcentaje:.2f}%</b></span><br>
<b>❗ Faltante:</b> <span style='color:red'>{formato_pesos(faltante)}</span>
</div>
"""
    return mensaje

def construir_grafico_cumplimiento_logic(total_actual, meta):
    if total_actual == 0 and meta == 0:
        fig = px.pie(names=["Sin datos"], values=[1], hole=0.6, color_discrete_sequence=["#e5e7eb"])
        fig.update_layout(title={"text":"Sin datos para graficar","x":0.5})
        return fig
        
    logrado = min(total_actual, meta)
    faltante = max(meta - total_actual, 0)
    
    # Si superó la meta
    if total_actual > meta:
        logrado = meta
        faltante = 0 
        
    datos = pd.DataFrame({"Estado": ["Logrado", "Faltante"], "Valor": [logrado, faltante]})
    fig = px.pie(
        datos,
        names="Estado",
        values="Valor",
        hole=0.5,
        color="Estado",
        color_discrete_map={"Logrado": "#22c55e", "Faltante": "#94a3b8"}
    )
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}: $ %{value:,.0f}")
    fig.update_layout(
        title={"text":"Cumplimiento de meta","x":0.5,"font":{"size":18,"color":"#0f172a"}},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False
    )
    return fig

def actualizar_cumplimiento(f1, f2, meta, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad):
    # Guardar meta si ha cambiado (y no es None)
    if meta is not None:
        guardar_meta("meta_cumplimiento.txt", meta)
    else:
        meta = cargar_meta("meta_cumplimiento.txt")
        
    # Calcular Total Filtrado
    df = leer_excel(f1, f2)
    df_filtrado, _ = filtrar_datos(df, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)
    
    total_actual = 0.0
    if df_filtrado is not None and not df_filtrado.empty:
        col_valor = next((c for c in df_filtrado.columns if str(c).strip().lower() == "valor"), None)
        if not col_valor:
            col_valor = next((c for c in df_filtrado.columns if "valor" in str(c).lower()), None)
            
        if col_valor:
            serie = pd.to_numeric(df_filtrado[col_valor], errors="coerce")
            total_actual = float(serie[serie > 0].sum())

    msg = calcular_cumplimiento_logic(total_actual, meta)
    fig = construir_grafico_cumplimiento_logic(total_actual, meta)
    return msg, fig

# ===================== GENERACIÓN DE INFORMES =====================
def generar_informe_excel(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad):
    df = leer_excel(f1, f2)
    df_filtrado, _ = filtrar_datos(df, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)
    
    if df_filtrado.empty:
        return None
    
    # Nombre del archivo temporal
    filename = "Informe_Generado_Goleman.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Pestaña 1: Datos Filtrados (Crudos)
        df_filtrado.to_excel(writer, sheet_name="Datos Filtrados", index=False)
        
        # Pestaña 2: Resumen Pacientes (Lógica replicada de actualizar_analisis)
        df_pacientes, _, _, _ = actualizar_analisis(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)
        if not df_pacientes.empty:
            df_pacientes.to_excel(writer, sheet_name="Resumen Pacientes", index=False)
            
        # Pestaña 3: Resumen Profesional x Procedimiento
        _, _, resumen_df, _ = actualizar_analisis(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)
        if not resumen_df.empty:
            resumen_df.to_excel(writer, sheet_name="Resumen Prof x Proc", index=False)
            
        # Pestaña 4: Totales Generales
        totales_proc = calcular_totales_por_procedimiento(df_filtrado)
        if not totales_proc.empty:
            totales_proc.to_excel(writer, sheet_name="Totales por Procedimiento", index=False)
            
    return filename

def limpiar_todo():
    global global_df, last_loaded_files, global_consolidado_path
    global_df = None
    last_loaded_files = (None, None)
    global_consolidado_path = None
    
    # Eliminar archivos físicos consolidado
    try:
        import glob
        for f in glob.glob("archivo_consolidado*.xlsx"):
            try:
                os.remove(f)
            except:
                pass
    except:
        pass
        
    return (
        gr.update(value=None), # archivo1
        gr.update(value=None), # archivo2
        gr.update(value=None, visible=False), # archivo_consolidado_output
        "⏳ Esperando archivos...", # fecha_update_lbl
        gr.update(value=None, choices=[]), # filtro_profesional_dropdown
        gr.update(value=None, choices=[]), # filtro_procedimiento_dropdown
        gr.update(value=None, choices=[]), # filtro_ciudad_dropdown
        gr.update(value=None), # filtro_fecha_inicio
        gr.update(value=None), # filtro_fecha_fin
        gr.update(value=pd.DataFrame()), # tabla
        "", # total_filtrado_md
        None, # resumen_state
        "", # resumen_html
        "", # aviso_fecha
        "<h2 style='text-align:center;color:darkblue'>💰 Total: $0</h2>", # total_valor_md
        "", # total_por_servicio_html
        "", # mensaje_dashboard
        "", # mensaje_ranking
        "", # mensaje_cumplimiento
        None, # grafico_cumplimiento
        gr.update(value=None, visible=False) # output_file_informe
    )

# ===================== INTERFAZ PRINCIPAL =====================
with gr.Blocks() as app:
    gr.Markdown("<h1 style='text-align:center; color:#005f73;'>IPS GOLEMAN</h1><p style='text-align:center; font-size:20px; color:#0a9396;'>Sistema técnico de análisis y control de datos</p>")
    notif_html = gr.HTML("")

    login_box = gr.Column(visible=True)
    main_app = gr.Column(visible=False)

    # ---------- LOGIN ----------
    with login_box:
        gr.Markdown("<div style='background: linear-gradient(to right, #e0f7fa, #ffffff); border-radius:20px; padding:40px; max-width:450px; margin:auto; box-shadow:0 6px 25px rgba(0,0,0,0.15); text-align:center;'><h1 style='color:#00796b;'>Inicio de sesión</h1><p style='color:#006064;'>Ingrese sus credenciales para continuar</p></div>")
        usuario = gr.Textbox(label="Usuario")
        contraseña = gr.Textbox(label="Contraseña", type="password")
        btn_login = gr.Button("Acceder", variant="primary")
        login_error = gr.Markdown("")
    # btn_login.click se mueve al final para incluir archivo en outputs

    # ---------- APP PRINCIPAL ----------
    with main_app:
        with gr.Row(elem_id="header_row", variant="panel"):
            with gr.Column(scale=4):
                 # Mensaje de fecha de actualización
                 fecha_update_lbl = gr.Markdown("⏳ Cargando fecha de actualización...")
            
            # Botones de acción organizados
            with gr.Column(scale=6):
                with gr.Row():
                    user_badge = gr.HTML(visible=False)
                    btn_home = gr.Button("🏠 Limpiar", variant="secondary")
                    btn_descargar_informe = gr.Button("� Descargar Informe", variant="secondary")
                    btn_logout = gr.Button("� Cerrar sesión", variant="stop")
        
        output_file_informe = gr.File(label="Descargar Informe Generado", visible=False)
        
        # Fila de archivos (dividida en 2)
        with gr.Row():
            archivo1 = gr.File(label="Subir Archivo Excel 1 (.xlsx)")
            archivo2 = gr.File(label="Subir Archivo Excel 2 (.xlsx) [Opcional]")
        
        # Output para archivo consolidado
        archivo_consolidado_output = gr.File(label="📥 Archivo CONSOLIDADO (Descargar)", visible=False, interactive=False)
        
        # Helper para sincronización de estado UI (Fecha + Consolidado)
        def sync_ui_state():
            fecha = cargar_fecha_actualizacion()
            msg = f"**🕒 Archivo actualizado:** {fecha}"
            
            import glob
            consolidados = glob.glob("archivo_consolidado*.xlsx")
            path = None
            if consolidados:
                path = consolidados[0]
            
            file_update = gr.update(visible=False)
            if path:
                msg += "<br><br><div style='background-color:#d1fae5; color:#065f46; padding:15px; border-radius:8px; text-align:center; font-size:18px; font-weight:bold; border: 2px solid #34d399; margin-top:10px;'>✅ ARCHIVO CONSOLIDADO GENERADO EXITOSAMENTE</div>"
                file_update = gr.update(value=path, visible=True)
            
            return msg, file_update

        # Timer para sincronización "tiempo real" (cada 2 seg)
        timer_sync = gr.Timer(2)
        timer_sync.tick(sync_ui_state, None, [fecha_update_lbl, archivo_consolidado_output])

        # Helper para cargar ambos archivos y actualizar todo
        def procesar_carga_archivos(file1, file2):
            # Leer y guardar
            leer_excel(file1, file2)
            # Retornar nueva fecha y archivo consolidado si existe
            return sync_ui_state()

        # ----------------------- TAB ANÁLISIS -----------------------
        with gr.Tab("ANÁLISIS"):
            gr.Markdown("<h2 style='text-align:center;color:orange'>📊 Análisis de Datos</h2>")

            # Dropdown for Professional Name
            filtro_profesional_dropdown = gr.Dropdown(
                label="📝 Profesional",
                choices=[],
                interactive=True
            )
            # Callbacks movidos al final

            # Dropdown for Procedure Name
            filtro_procedimiento_dropdown = gr.Dropdown(
                label="📝 Nombre procedimiento",
                choices=[],
                interactive=True
            )

            # Dropdown for Ciudad
            filtro_ciudad_dropdown = gr.Dropdown(
                label="📍 Ciudad / Municipio",
                choices=[],
                interactive=True
            )

            with gr.Row():
                filtro_fecha_inicio = gr.DateTime(label="📅 Fecha Inicio", include_time=False, type="datetime")
                filtro_fecha_fin = gr.DateTime(label="📅 Fecha Fin", include_time=False, type="datetime")

            aviso_fecha = gr.Markdown()
            with gr.Row():
                aplicar_filtro_btn = gr.Button("Aplicar filtro", variant="primary")
                btn_recargar_analisis = gr.Button("↻ Recargar", variant="secondary")
            
            # Tabla principal (ahora agrupada por paciente)
            tabla = gr.Dataframe(label="Resumen por Paciente")
            
            # Solo mostramos el total filtrado en Markdown/HTML, eliminamos el dataframe 'totales'
            total_filtrado_md = gr.Markdown()
            
            # Estado oculto para el dataframe de resumen (no se muestra, pero se calcula)
            resumen_state = gr.State()

            # HTML de resumen ocupa todo el ancho
            resumen_html = gr.HTML()

            # Outputs: tabla principal, total html, resumen df (hidden state), aviso
            outputs_analisis = [tabla, total_filtrado_md, resumen_state, aviso_fecha]

            # Nota: Los callbacks y change events se han movido al final del archivo para manejar archivo1/archivo2
            
            # Wrapper para el resumen HTML
            def actualizar_resumen_html_wrapper(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad):
                _, _, resumen_df, _ = actualizar_analisis(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)
                return render_resumen_html(resumen_df, "Resumen Profesional × Procedimiento")
            
            archivo1.upload(procesar_carga_archivos, [archivo1, archivo2], [fecha_update_lbl, archivo_consolidado_output], queue=False, show_progress="hidden")
            archivo2.upload(procesar_carga_archivos, [archivo1, archivo2], [fecha_update_lbl, archivo_consolidado_output], queue=False, show_progress="hidden")

            def reset_analisis(f1, f2):
                tabla_v, total_html_v, resumen_df_v, aviso_v = actualizar_analisis(f1, f2, None, None, None, None, None)
                return (
                    gr.update(value=None), # Prof
                    gr.update(value=None), # Proc
                    gr.update(value=None), # Inicio
                    gr.update(value=None), # Fin
                    gr.update(value=None), # Ciudad
                    tabla_v,
                    total_html_v,
                    resumen_df_v,
                    render_resumen_html(resumen_df_v, "Resumen Profesional × Procedimiento"),
                    aviso_v
                )
            # (Callback moved to end of file to ensure all components are defined)


        # ---- TAB TOTAL ----
        with gr.Tab("TOTAL"):
            total_valor_md = gr.Markdown("<h2 style='text-align:center;color:darkblue'>💰 Total: $0</h2>")
            with gr.Row():
                with gr.Column(scale=1):
                    total_por_servicio_html = gr.HTML()

            def actualizar_total(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad):
                df = leer_excel(f1, f2)
                df_filtrado, _ = filtrar_datos(df, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)
                
                totales_df = calcular_totales(df_filtrado)
                valor_total = totales_df.iloc[0,0] if totales_df is not None else "❌"
                resumen_servicios = calcular_totales_por_procedimiento(df_filtrado)
                datos_num = calcular_totales_por_procedimiento_numerico(df_filtrado)
                if datos_num is not None and not datos_num.empty:
                    datos_num = datos_num.sort_values("Valor_Total_Num", ascending=False)
                    fig = px.bar(
                        datos_num,
                        x="Procedimiento",
                        y="Valor_Total_Num",
                        text="Valor_Total_Num",
                        color="Procedimiento",
                        color_discrete_sequence=[
                            "#3b82f6","#8b5cf6","#06b6d4","#10b981","#f59e0b","#ef4444",
                            "#14b8a6","#f97316","#22c55e","#a855f7","#0ea5e9","#f43f5e"
                        ]
                    )
                    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", hovertemplate="%{x}<br>$ %{y:,.0f}")
                    fig.update_layout(
                        title={"text":"Valor por procedimiento","x":0.5,"font":{"size":18,"color":"#0f172a"}},
                        xaxis_title="Nombre procedimiento",
                        yaxis_title="Valor total",
                        paper_bgcolor="#ffffff",
                        plot_bgcolor="#ffffff",
                        margin=dict(l=40, r=20, t=60, b=80),
                        showlegend=False
                    )
                else:
                    fig = px.bar(pd.DataFrame({'x':[], 'y':[]}), x='x', y='y')
                    fig.update_layout(
                        title={"text":"Sin datos para graficar","x":0.5,"font":{"size":16,"color":"#334155"}},
                        paper_bgcolor="#ffffff",
                        plot_bgcolor="#ffffff",
                        margin=dict(l=10, r=10, t=40, b=10),
                        showlegend=False
                    )
                html_resumen = ""
                if resumen_servicios is not None and not resumen_servicios.empty:
                    # Construir HTML con barras proporcionales
                    try:
                        # Obtener valores numéricos sin formato para escala
                        vals = []
                        for v in resumen_servicios["Valor_Total"]:
                            try:
                                # quitar símbolos para cálculo aprox
                                n = float(str(v).replace("$", "").replace(".", "").replace(",", ".").strip())
                                vals.append(n)
                            except:
                                vals.append(0)
                        maxv = max(vals) if vals else 1
                        html_resumen = "<div style='background:#f8fafc;padding:16px;border-radius:16px'><h3 style='color:#1e40af;margin:0 0 12px 0'>Totales por procedimiento</h3>"
                        for i, row in resumen_servicios.head(20).iterrows():
                            nombre = row[resumen_servicios.columns[0]]
                            valor = row["Valor_Total"]
                            ancho = int(((vals[i] if i < len(vals) else 0) / maxv) * 100)
                            color = ["#3b82f6","#8b5cf6","#06b6d4","#10b981","#f59e0b","#ef4444"][i % 6]
                            bar_id = f"bar_{i}"
                            name_id = f"name_{i}"
                            html_resumen += f"""
                            <div style='margin-bottom:10px;cursor:pointer' title='Click para resaltar'
                                 onclick="(function(){{var b=document.getElementById('{bar_id}'); if(b){{b.style.background='#22c55e';}} var n=document.getElementById('{name_id}'); if(n){{n.style.color='#16a34a';}}}})()">
                                <div style='display:flex;justify-content:space-between'><span id='{name_id}' style='font-weight:600;color:#334155'>{nombre}</span><span style='color:#0f766e'>{valor}</span></div>
                                <div style='background:#e5e7eb;border-radius:8px;height:10px'>
                                    <div id='{bar_id}' style='background:{color};width:{ancho}%;height:10px;border-radius:8px;transition:background-color .2s ease'></div>
                                </div>
                            </div>
                            """
                        html_resumen += "</div>"
                    except:
                        html_resumen = "<div style='background:#fff3cd;color:#856404;padding:12px;border-radius:10px'>No se pudo renderizar resumen</div>"
                return (
                    f"<div style='text-align:center; background:#e0fbfc; padding:20px; border-radius:15px;'><h1 style='color:#005f73;'>💰 Total: {valor_total}</h1></div>",
                    html_resumen
                )

        # ---- TAB DASHBOARD PROFESIONAL ----
        with gr.Tab("DASHBOARD PROFESIONAL"):
            gr.Markdown("<h2 style='text-align:center;color:purple'>📊 Dashboard Profesional</h2>")
            meta_general_input = gr.Number(label="🎯 Meta General Dashboard (Editable)",
                                           value=cargar_meta("meta_dashboard.txt"), interactive=True)

            with gr.Row():
                with gr.Column(scale=2):
                    mensaje_dashboard = gr.HTML()
                with gr.Column(scale=1):
                    mensaje_ranking = gr.HTML()

            def actualizar_dashboard(f1, f2, meta_valor, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad):
                df = leer_excel(f1, f2)
                df_filtrado, _ = filtrar_datos(df, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)
                return generar_dashboard_profesional(df_filtrado, meta_valor)

        # ---- TAB CUMPLIMIENTO ----
        with gr.Tab("CUMPLIMIENTO"):
            meta_cumplimiento = gr.Number(label="🎯 Meta Cumplimiento", value=cargar_meta("meta_cumplimiento.txt"), interactive=True)
            mensaje_cumplimiento = gr.HTML()
            grafico_cumplimiento = gr.Plot()

    # ===================== CALLBACKS ACTUALIZADOS =====================
    
    # 1. Definir listas de inputs con 2 archivos
    inputs_analisis = [archivo1, archivo2, filtro_profesional_dropdown, filtro_fecha_inicio, filtro_fecha_fin, filtro_procedimiento_dropdown, filtro_ciudad_dropdown]
    inputs_sync = [archivo1, archivo2, filtro_profesional_dropdown, filtro_fecha_inicio, filtro_fecha_fin, filtro_procedimiento_dropdown, filtro_ciudad_dropdown]
    inputs_dashboard = [archivo1, archivo2, meta_general_input, filtro_profesional_dropdown, filtro_fecha_inicio, filtro_fecha_fin, filtro_procedimiento_dropdown, filtro_ciudad_dropdown]
    inputs_cumplimiento = [archivo1, archivo2, meta_cumplimiento, filtro_profesional_dropdown, filtro_fecha_inicio, filtro_fecha_fin, filtro_procedimiento_dropdown, filtro_ciudad_dropdown]

    # 2. Re-bindear eventos de la pestaña ANÁLISIS
    # Eventos de actualización de tablas/gráficos
    aplicar_filtro_btn.click(actualizar_analisis, inputs_analisis, outputs_analisis, queue=False, show_progress="minimal")
    aplicar_filtro_btn.click(actualizar_resumen_html_wrapper, inputs_analisis, [resumen_html], queue=False, show_progress="hidden")
    
    for inp in [filtro_profesional_dropdown, filtro_procedimiento_dropdown, filtro_ciudad_dropdown]:
        inp.change(actualizar_analisis, inputs_analisis, outputs_analisis, queue=False, show_progress="minimal")
        inp.change(actualizar_resumen_html_wrapper, inputs_analisis, [resumen_html], queue=False, show_progress="hidden")

    # Botón recargar
    btn_recargar_analisis.click(
        reset_analisis,
        [archivo1, archivo2],
        [filtro_profesional_dropdown, filtro_procedimiento_dropdown, filtro_fecha_inicio, filtro_fecha_fin, filtro_ciudad_dropdown, tabla, total_filtrado_md, resumen_state, resumen_html, aviso_fecha],
        queue=False,
        show_progress="hidden"
    )

    # 3. Callbacks para cargar opciones de dropdowns (al subir archivo)
    archivo1.upload(cargar_profesionales, [archivo1, archivo2], filtro_profesional_dropdown, queue=False)
    archivo1.upload(cargar_procedimientos, [archivo1, archivo2], filtro_procedimiento_dropdown, queue=False)
    archivo1.upload(cargar_ciudades, [archivo1, archivo2], filtro_ciudad_dropdown, queue=False)
    
    archivo2.upload(cargar_profesionales, [archivo1, archivo2], filtro_profesional_dropdown, queue=False)
    archivo2.upload(cargar_procedimientos, [archivo1, archivo2], filtro_procedimiento_dropdown, queue=False)
    archivo2.upload(cargar_ciudades, [archivo1, archivo2], filtro_ciudad_dropdown, queue=False)

    # Actualizar todo el dashboard al subir archivos
    for arch in [archivo1, archivo2]:
        arch.upload(actualizar_analisis, inputs_analisis, outputs_analisis, queue=False, show_progress="hidden")
        arch.upload(actualizar_resumen_html_wrapper, inputs_analisis, [resumen_html], queue=False, show_progress="hidden")
        arch.upload(actualizar_total, inputs_sync, [total_valor_md, total_por_servicio_html], queue=False, show_progress="hidden")
        arch.upload(actualizar_dashboard, inputs_dashboard, [mensaje_dashboard, mensaje_ranking], queue=False, show_progress="hidden")
        arch.upload(actualizar_cumplimiento, inputs_cumplimiento, [mensaje_cumplimiento, grafico_cumplimiento], queue=False, show_progress="hidden")

    # 4. Sincronización TOTAL
    aplicar_filtro_btn.click(actualizar_total, inputs_sync, [total_valor_md, total_por_servicio_html], queue=False, show_progress="hidden")
    for inp in [filtro_profesional_dropdown, filtro_procedimiento_dropdown, filtro_ciudad_dropdown]:
         inp.change(actualizar_total, inputs_sync, [total_valor_md, total_por_servicio_html], queue=False, show_progress="hidden")
         
    # 5. Sincronización DASHBOARD
    aplicar_filtro_btn.click(actualizar_dashboard, inputs_dashboard, [mensaje_dashboard, mensaje_ranking], queue=False, show_progress="hidden")
    for inp in [filtro_profesional_dropdown, filtro_procedimiento_dropdown, filtro_ciudad_dropdown, meta_general_input]:
        inp.change(actualizar_dashboard, inputs_dashboard, [mensaje_dashboard, mensaje_ranking], queue=False, show_progress="hidden")

    # 6. Sincronización CUMPLIMIENTO
    aplicar_filtro_btn.click(actualizar_cumplimiento, inputs_cumplimiento, [mensaje_cumplimiento, grafico_cumplimiento], queue=False, show_progress="hidden")
    for inp in [filtro_profesional_dropdown, filtro_procedimiento_dropdown, filtro_ciudad_dropdown, meta_cumplimiento]:
        inp.change(actualizar_cumplimiento, inputs_cumplimiento, [mensaje_cumplimiento, grafico_cumplimiento], queue=False, show_progress="hidden")

    # ---- CALLBACK INICIALIZACIÓN (al final para ver todos los componentes) ----
    def inicializar_post_login():
        # Asegurar carga de datos (desde disco si es necesario)
        leer_excel(None, None)
        
        # Cargar estado previo
        state = cargar_estado_filtros()
        
        prof_val = state.get("profesional")
        proc_val = state.get("procedimiento")
        ciud_val = state.get("ciudad")
        ini_val = state.get("fecha_inicio")
        fin_val = state.get("fecha_fin")
        
        # Cargar opciones
        prof_dd = cargar_profesionales(None, None)
        proc_dd = cargar_procedimientos(None, None)
        ciud_dd = cargar_ciudades(None, None)
        
        # Restaurar valores si existen en las opciones
        if prof_val and prof_dd.get('choices') and prof_val in prof_dd['choices']:
            prof_dd['value'] = prof_val
        
        if proc_val and proc_dd.get('choices') and proc_val in proc_dd['choices']:
            proc_dd['value'] = proc_val
            
        if ciud_val and ciud_dd.get('choices') and ciud_val in ciud_dd['choices']:
            ciud_dd['value'] = ciud_val

        # Ejecutar análisis con estado restaurado
        tabla_v, total_html_v, resumen_df_v, aviso_v = actualizar_analisis(None, None, prof_val, ini_val, fin_val, proc_val, ciud_val)
        resumen_html_v = render_resumen_html(resumen_df_v, "Resumen Profesional × Procedimiento")
        
        # Ejecutar cálculo de TOTAL (persistencia)
        total_val_md_v, total_serv_html_v = actualizar_total(None, None, prof_val, ini_val, fin_val, proc_val, ciud_val)

        # Ejecutar DASHBOARD PROFESIONAL
        meta_g = cargar_meta("meta_dashboard.txt")
        dash_msg_v, dash_rank_v = actualizar_dashboard(None, None, meta_g, prof_val, ini_val, fin_val, proc_val, ciud_val)

        return prof_dd, proc_dd, ciud_dd, ini_val, fin_val, tabla_v, total_html_v, resumen_df_v, resumen_html_v, aviso_v, total_val_md_v, total_serv_html_v, dash_msg_v, dash_rank_v
    
    btn_login.click(
        inicializar_post_login,
        None,
        [filtro_profesional_dropdown, filtro_procedimiento_dropdown, filtro_ciudad_dropdown, filtro_fecha_inicio, filtro_fecha_fin, tabla, total_filtrado_md, resumen_state, resumen_html, aviso_fecha, total_valor_md, total_por_servicio_html, mensaje_dashboard, mensaje_ranking],
        queue=False,
        show_progress="hidden"
    )

    # ---- CALLBACK LIMPIAR / HOME ----
    btn_home.click(
        limpiar_todo,
        None,
        [
            archivo1, archivo2, archivo_consolidado_output, fecha_update_lbl,
            filtro_profesional_dropdown, filtro_procedimiento_dropdown, filtro_ciudad_dropdown,
            filtro_fecha_inicio, filtro_fecha_fin,
            tabla, total_filtrado_md, resumen_state, resumen_html, aviso_fecha,
            total_valor_md, total_por_servicio_html,
            mensaje_dashboard, mensaje_ranking,
            mensaje_cumplimiento, grafico_cumplimiento,
            output_file_informe
        ],
        queue=False,
        show_progress="minimal"
    )

    # ---- CALLBACK LOGOUT (al final para ver todos los componentes) ----
    btn_logout.click(cerrar_sesion, None, [login_box, main_app, notif_html, filtro_profesional_dropdown, filtro_procedimiento_dropdown, filtro_ciudad_dropdown, filtro_fecha_inicio, filtro_fecha_fin, user_badge])

    # Inicializar Cumplimiento al login
    btn_login.click(actualizar_cumplimiento, inputs_cumplimiento, [mensaje_cumplimiento, grafico_cumplimiento], queue=False, show_progress="hidden")

    # Listener principal de Login (mueve visibilidad de archivo)
    btn_login.click(login, [usuario, contraseña], [login_box, main_app, login_error, notif_html, archivo1, archivo2, meta_general_input, user_badge, archivo_consolidado_output], queue=False)

    # Listener Descargar Informe
    inputs_informe = [archivo1, archivo2, filtro_profesional_dropdown, filtro_fecha_inicio, filtro_fecha_fin, filtro_procedimiento_dropdown, filtro_ciudad_dropdown]
    
    def mostrar_archivo_descarga(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad):
        path = generar_informe_excel(f1, f2, nombre_prof, fecha_inicio, fecha_fin, procedimiento, ciudad)
        if path:
            return gr.update(value=path, visible=True)
        return gr.update(visible=False)

    btn_descargar_informe.click(mostrar_archivo_descarga, inputs_informe, [output_file_informe], queue=False)

if __name__ == "__main__":
    print("Iniciando servidor Gradio...")
    app.launch(share=False, prevent_thread_lock=True)
    print("Servidor iniciado. Presione Ctrl+C para detener.")
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Cerrando...")

