# 🤝 Contribuir a NestSecure

¡Gracias por tu interés en contribuir a NestSecure! Este documento te guiará en el proceso.

## 📋 Cómo Contribuir

### 1. Fork del Proyecto
1. Haz click en el botón **Fork** arriba a la derecha
2. Esto crea una copia del proyecto en tu cuenta

### 2. Clona tu Fork
```bash
git clone https://github.com/TU_USUARIO/nestsecure.git
cd nestsecure
```

### 3. Crea una Rama para tu Feature
```bash
git checkout -b feature/nombre-descriptivo
# Ejemplos:
# - feature/add-nessus-scanner
# - fix/memory-leak-redis
# - docs/improve-installation-guide
```

### 4. Haz tus Cambios
- Escribe código limpio y bien comentado
- Sigue las convenciones del proyecto
- Incluye tests para nuevas funcionalidades
- Actualiza la documentación si es necesario

### 5. Ejecuta los Tests
```bash
cd backend
source venv/bin/activate
pytest -v
```

### 6. Commit tus Cambios
```bash
git add .
git commit -m "feat: descripción clara del cambio"
```

**Formato de commits:**
- `feat:` nueva funcionalidad
- `fix:` corrección de bug
- `docs:` cambios en documentación
- `test:` añadir o modificar tests
- `refactor:` refactorización de código
- `style:` cambios de formato (no afectan funcionalidad)

### 7. Push a tu Fork
```bash
git push origin feature/nombre-descriptivo
```

### 8. Crea un Pull Request
1. Ve a tu fork en GitHub
2. Click en **Compare & pull request**
3. Describe claramente qué cambios hiciste y por qué
4. Espera la revisión del maintainer

## 🎯 Lineamientos

### Código
- Python 3.11+
- Usa type hints
- Docstrings en funciones públicas
- Máximo 100 caracteres por línea

### Tests
- Cobertura mínima: 80%
- Tests unitarios para lógica de negocio
- Tests de integración para APIs

### Documentación
- README claro y actualizado
- Comentarios en código complejo
- Docstrings en formato Google Style

## 🐛 Reportar Bugs

Usa el sistema de Issues de GitHub:
1. Busca si el bug ya fue reportado
2. Si no existe, crea un nuevo Issue
3. Incluye:
   - Descripción clara del problema
   - Pasos para reproducir
   - Comportamiento esperado vs actual
   - Logs o screenshots si aplica
   - Tu entorno (OS, Python version, etc.)

## 💡 Proponer Features

1. Abre un Issue con la etiqueta `feature-request`
2. Describe:
   - Qué problema resuelve
   - Propuesta de solución
   - Alternativas consideradas
3. Espera feedback antes de implementar

## ❓ Preguntas

Si tienes dudas, abre un Issue con la etiqueta `question`.

## 📜 Código de Conducta

- Sé respetuoso y constructivo
- No se tolera acoso ni discriminación
- Enfócate en el código, no en las personas
- Acepta críticas constructivas

## 🙏 Agradecimientos

Todas las contribuciones son valoradas, sin importar su tamaño. ¡Gracias por hacer NestSecure mejor!

---

**Nota:** El maintainer (@ramjavii) revisará todos los PRs. Por favor ten paciencia, esto es un proyecto personal y las revisiones pueden tomar tiempo.
