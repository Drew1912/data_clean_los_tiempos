import pandas as pd
import os
from datetime import datetime
import logging

# Configure basic logging for the processor
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self, logs_dir="logs", reports_dir="reports"):
        self.logs_dir = logs_dir
        self.reports_dir = reports_dir
        
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Setup file handler for this processor
        log_file = os.path.join(self.logs_dir, f"process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)

    def load_data(self, file_path):
        """Loads data from Excel, CSV or TXT"""
        try:
            logger.info(f"Loading file: {file_path}")
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.xlsx', '.xls']:
                return pd.read_excel(file_path)
            elif ext == '.csv':
                return pd.read_csv(file_path)
            elif ext == '.txt':
                # Assuming tab separated or pipe separated, fallback to csv read with sep='\t' or '|'
                # Defaulting to tab separated for TXT
                return pd.read_csv(file_path, sep='\t')
            else:
                raise ValueError(f"Unsupported file extension: {ext}")
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {str(e)}")
            raise

    def clean_data(self, df, source_name):
        """
        Cleans the dataframe:
        - Removes blank rows for key columns
        - Standardizes date and currency
        """
        logger.info(f"Cleaning data for: {source_name}")
        
        # Standardize column names to uppercase and strip spaces for easier matching
        df.columns = df.columns.str.strip().str.upper()
        
        # We assume the columns exist or are very similar to these
        col_nit = next((col for col in df.columns if 'NIT' in col), None)
        col_fecha = next((col for col in df.columns if 'FECHA' in col), None)
        col_monto = next((col for col in df.columns if 'MONTO' in col or 'IMPORTE' in col or 'TOTAL' in col), None)
        
        if not all([col_nit, col_fecha, col_monto]):
            raise ValueError(f"Could not find all required key columns (NIT, FECHA, MONTO/TOTAL) in {source_name}. Found: NIT={col_nit}, FECHA={col_fecha}, MONTO={col_monto}")
        
        # Rename to standard internal names
        df = df.rename(columns={col_nit: 'NIT_KEY', col_fecha: 'FECHA_KEY', col_monto: 'MONTO_KEY'})
        
        # 1. Remove rows where any of the keys are missing
        initial_count = len(df)
        df = df.dropna(subset=['NIT_KEY', 'FECHA_KEY', 'MONTO_KEY'])
        logger.info(f"{source_name}: Removed {initial_count - len(df)} rows with missing key data.")
        
        # 2. Standardize Date (FECHA_KEY)
        try:
            df['FECHA_KEY'] = pd.to_datetime(df['FECHA_KEY'], errors='coerce').dt.date
        except Exception as e:
            logger.warning(f"Error parsing dates in {source_name}: {e}")
            
        # 3. Standardize Monto (Numeric, round to 2 decimals)
        try:
            # Replace commas with dots if string, then convert to numeric
            if df['MONTO_KEY'].dtype == object:
                df['MONTO_KEY'] = df['MONTO_KEY'].astype(str).str.replace(',', '.')
            df['MONTO_KEY'] = pd.to_numeric(df['MONTO_KEY'], errors='coerce').round(2)
        except Exception as e:
            logger.warning(f"Error parsing amounts in {source_name}: {e}")
            
        # Drop rows that became NaT or NaN after conversion
        df = df.dropna(subset=['NIT_KEY', 'FECHA_KEY', 'MONTO_KEY'])
        
        # Convert NIT to string and strip just in case
        df['NIT_KEY'] = df['NIT_KEY'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        
        logger.info(f"{source_name}: Data cleaned. Rows remaining: {len(df)}")
        return df

    def process_files(self, ventas_path, contabilidad_path):
        """
        Main engine to cross data.
        """
        logger.info("Starting data processing cycle.")
        try:
            df_ventas = self.load_data(ventas_path)
            df_conta = self.load_data(contabilidad_path)
            
            df_ventas_clean = self.clean_data(df_ventas, "Ventas")
            df_conta_clean = self.clean_data(df_conta, "Contabilidad")
            
            # Add identifiers
            df_ventas_clean['ORIGEN'] = 'VENTAS'
            df_conta_clean['ORIGEN'] = 'CONTABILIDAD'
            
            # Perform the cross-match (Merge)
            # We want to find exact matches, and discrepancies.
            # An outer join will let us see what matched and what didn't.
            keys = ['NIT_KEY', 'FECHA_KEY', 'MONTO_KEY']
            
            merged = pd.merge(
                df_ventas_clean, 
                df_conta_clean, 
                on=keys, 
                how='outer', 
                indicator=True,
                suffixes=('_VENTAS', '_CONTA')
            )
            
            # indicator=True adds a column '_merge' with values: 'left_only', 'right_only', 'both'
            
            # Map the _merge column to status
            status_map = {
                'both': 'Validado / Coincidencia Exacta',
                'left_only': 'Discrepancia: Solo en Ventas',
                'right_only': 'Discrepancia: Solo en Contabilidad'
            }
            merged['ESTADO_CRUCE'] = merged['_merge'].map(status_map)
            merged = merged.drop(columns=['_merge'])
            
            # Statistics for log
            total_ventas = len(df_ventas_clean)
            total_conta = len(df_conta_clean)
            coincidencias = len(merged[merged['ESTADO_CRUCE'] == 'Validado / Coincidencia Exacta'])
            discrepancias_ventas = len(merged[merged['ESTADO_CRUCE'] == 'Discrepancia: Solo en Ventas'])
            discrepancias_conta = len(merged[merged['ESTADO_CRUCE'] == 'Discrepancia: Solo en Contabilidad'])
            
            logger.info(f"Cruce Summary: Total Ventas={total_ventas}, Total Contabilidad={total_conta}")
            logger.info(f"Coincidencias: {coincidencias}")
            logger.info(f"Discrepancias (Solo Ventas): {discrepancias_ventas}")
            logger.info(f"Discrepancias (Solo Contabilidad): {discrepancias_conta}")
            
            # Save the report
            report_name = f"Reporte_Cruce_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            report_path = os.path.join(self.reports_dir, report_name)
            
            # Organize output columns to put keys and status first
            cols = ['ESTADO_CRUCE'] + keys + [c for c in merged.columns if c not in keys + ['ESTADO_CRUCE']]
            merged = merged[cols]
            
            merged.to_excel(report_path, index=False)
            logger.info(f"Report generated successfully at: {report_path}")
            
            return {
                "status": "success",
                "message": "Cruce realizado exitosamente.",
                "report_file": report_name,
                "stats": {
                    "total_ventas_procesadas": total_ventas,
                    "total_conta_procesadas": total_conta,
                    "coincidencias": coincidencias,
                    "discrepancias_solo_ventas": discrepancias_ventas,
                    "discrepancias_solo_contabilidad": discrepancias_conta
                }
            }
            
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
