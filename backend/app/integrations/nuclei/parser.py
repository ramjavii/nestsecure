# =============================================================================
# NESTSECURE - Nuclei Output Parser
# =============================================================================
"""
Parser para resultados de Nuclei en formato JSON Lines.

Este módulo procesa el output JSON de Nuclei y lo convierte en
objetos Python tipados para fácil manipulación.

Características:
- Parseo de JSON Lines (JSONL)
- Extracción de findings con template info
- Soporte para diferentes versiones de Nuclei
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterator
from io import StringIO

from .models import (
    NucleiScanResult,
    NucleiFinding,
    NucleiTemplate,
    NucleiMatcher,
    Severity,
)
from .exceptions import NucleiParseError


class NucleiParser:
    """
    Parser para output JSON de Nuclei.
    
    Nuclei produce output en formato JSON Lines (una línea JSON por hallazgo).
    Este parser procesa ese output y genera objetos tipados.
    
    Uso:
        parser = NucleiParser()
        result = parser.parse_output(json_lines_output)
        
        for finding in result.findings:
            print(f"{finding.severity}: {finding.title}")
    """
    
    def __init__(self):
        """Inicializar parser."""
        self._finding_count = 0
    
    def parse_output(self, output: str) -> NucleiScanResult:
        """
        Parsear output completo de Nuclei.
        
        Args:
            output: Output JSON Lines de Nuclei
            
        Returns:
            NucleiScanResult con todos los findings
            
        Raises:
            NucleiParseError: Si hay error parseando
        """
        result = NucleiScanResult()
        result.start_time = datetime.now()
        
        findings = []
        templates_seen = set()
        hosts_seen = set()
        
        for line_num, finding in enumerate(self._parse_lines(output), 1):
            if finding:
                findings.append(finding)
                templates_seen.add(finding.template.id)
                hosts_seen.add(finding.host)
        
        result.findings = findings
        result.templates_used = sorted(list(templates_seen))
        result.targets = sorted(list(hosts_seen))
        result.matched_requests = len(findings)
        result.end_time = datetime.now()
        
        return result
    
    def parse_file(self, filepath: str) -> NucleiScanResult:
        """
        Parsear archivo de output Nuclei.
        
        Args:
            filepath: Ruta al archivo JSON Lines
            
        Returns:
            NucleiScanResult
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return self.parse_output(f.read())
        except FileNotFoundError:
            raise NucleiParseError(
                f"Output file not found: {filepath}"
            )
        except Exception as e:
            raise NucleiParseError(
                f"Error reading file: {str(e)}"
            )
    
    def parse_stream(self, stream: Iterator[str]) -> Iterator[NucleiFinding]:
        """
        Parsear stream de líneas JSON.
        
        Útil para procesar output en tiempo real.
        
        Args:
            stream: Iterador de líneas
            
        Yields:
            NucleiFinding para cada hallazgo
        """
        for line in stream:
            finding = self._parse_line(line)
            if finding:
                yield finding
    
    def _parse_lines(self, output: str) -> Iterator[Optional[NucleiFinding]]:
        """
        Parsear líneas de output.
        
        Args:
            output: Output completo
            
        Yields:
            NucleiFinding o None para cada línea
        """
        for line_num, line in enumerate(output.strip().split('\n'), 1):
            if not line.strip():
                continue
            
            try:
                yield self._parse_line(line, line_num)
            except NucleiParseError:
                raise
            except Exception as e:
                # Log pero continuar con otras líneas
                yield None
    
    def _parse_line(
        self,
        line: str,
        line_num: int = 0
    ) -> Optional[NucleiFinding]:
        """
        Parsear una línea JSON.
        
        Args:
            line: Línea JSON
            line_num: Número de línea (para errores)
            
        Returns:
            NucleiFinding o None si la línea está vacía
        """
        line = line.strip()
        if not line:
            return None
        
        # Ignorar líneas que no son JSON (logs de Nuclei)
        if not line.startswith('{'):
            return None
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            raise NucleiParseError(
                f"Invalid JSON at line {line_num}: {str(e)}",
                raw_output=line,
                line_number=line_num
            )
        
        # Crear finding desde JSON
        return NucleiFinding.from_json_line(data)
    
    def extract_stats(self, stderr: str) -> Dict[str, Any]:
        """
        Extraer estadísticas del stderr de Nuclei.
        
        Nuclei imprime estadísticas en stderr al finalizar.
        
        Args:
            stderr: Output de stderr
            
        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "total_requests": 0,
            "matched": 0,
            "errors": 0,
            "duration": None,
        }
        
        for line in stderr.split('\n'):
            line_lower = line.lower()
            
            # Buscar patrones de estadísticas
            if 'requests' in line_lower:
                # Intentar extraer número
                import re
                match = re.search(r'(\d+)\s*requests', line_lower)
                if match:
                    stats["total_requests"] = int(match.group(1))
            
            if 'matched' in line_lower:
                import re
                match = re.search(r'(\d+)\s*matched', line_lower)
                if match:
                    stats["matched"] = int(match.group(1))
            
            if 'error' in line_lower:
                import re
                match = re.search(r'(\d+)\s*error', line_lower)
                if match:
                    stats["errors"] = int(match.group(1))
        
        return stats


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def parse_nuclei_output(output: str) -> NucleiScanResult:
    """
    Parsear output JSON Lines de Nuclei.
    
    Función de conveniencia.
    
    Args:
        output: Output JSON Lines
        
    Returns:
        NucleiScanResult
    """
    parser = NucleiParser()
    return parser.parse_output(output)


def parse_nuclei_file(filepath: str) -> NucleiScanResult:
    """
    Parsear archivo de output Nuclei.
    
    Función de conveniencia.
    
    Args:
        filepath: Ruta al archivo
        
    Returns:
        NucleiScanResult
    """
    parser = NucleiParser()
    return parser.parse_file(filepath)
