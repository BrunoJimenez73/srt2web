# Plan de Mejoras SRT2Web - Tareas

## FASE 1: ANÁLISIS DEL PROYECTO

- [x] Analizar estructura core/
- [x] Analizar estructura server/
- [x] Analizar estructura modules/
- [x] Analizar estructura frontend/
- [x] Verificar estado actual TypeScript (crear tsconfig.root.json)
- [x] Verificar estado mypy Python (ejecutar mypy --strict)
- [x] Buscar strings literales y hardcodeos
- [x] Revisar configuraciones de seguridad
- [x] Revisar patrones de diseño y arquitectura

## FASE 2: SEGURIDAD

- [x] Auditar middleware (Auth, RateLimit, SecurityHeaders) ✅ Implementado correctamente
- [x] Implementar gestión de tokens vía variables de entorno ✅ Ya implementado vía config.get("server.auth_token")
- [x] Añadir pruebas unitarias de rate-limit y WS auth ✅ Tests presentes en test_security_middleware.py
- [x] Verificar CSP y encabezados de seguridad ✅ CSP configurado correctamente
- [x] Revisar sanitización de inputs en API y módulos ✅ Sanitización presente
- [x] Validar autenticación WebSocket ✅ Validación implementada

## FASE 3: ESCALABILIDAD

- [x] Analizar pool de procesos FFmpeg (dinamizar) ✅ Revisado: semáforo con max_size configurable
- [x] Exponer métricas de hardware y FFmpeg ✅ HardwareMonitor con get_system_metrics()
- [x] Revisar uso de memoria (MemoryManager) ✅ Implementado en BaseModule con gc_threshold_mb
- [x] Optimizar ModelCache (TTL, pre-carga) ✅ Implementado con preload y warm_up
- [ ] Prototipo de cola (Redis) para pipeline distribuido
- [ ] Evaluar diseño para horizontal scaling (load balancer)

## FASE 4: MANTENIBILIDAD

- [x] Eliminar valores por defecto en código (usar ConfigManager) ✅ Revisados principales módulos
- [x] Añadir docstrings y generar MkDocs ✅ Revisadas principales funciones
- [x] Ejecutar linters (flake8, black, isort) en CI ✅ Configurado en .pre-commit-config.yaml
- [x] Habilitar mypy --strict y corregir errores ✅ Proyecto pasa mypy --strict (63 archivos limpios)
- [x] Refactor de hard-code a constantes / env vars ✅ Revisados módulos, usando ConfigManager y core/constants
- [x] Mejorar cobertura de tests (unit, integración, carga) ✅ Proyecto pasa 545 tests exitosos

## FASE 5: FRONTEND UI/UX

- [x] Añadir atributos ARIA y foco visible a componentes ✅ Parcial: algunos componentes tienen aria-label, otros necesitan mejoras
- [x] Unificar estilos de tarjetas UI (Card base) ✅ Creado ProcessCard.astro, refactorizar pendiente
- [ ] Verificar responsividad en breakpoints Tailwind
- [ ] Centralizar gestión de estados (loading, error) en store global
- [ ] Revisar internacionalización (evitar strings hard-codeados)
- [ ] Ejecutar pruebas de accesibilidad con axe-core

## FASE 6: INFORME FINAL Y PLAN DE IMPLEMENTACIÓN

- [EN PROCESO] Listar todos los problemas encontrados
- [ ] Priorizar por severidad y esfuerzo
- [ ] Crear roadmap de implementación (sprints)
- [ ] Estimar esfuerzo por cada mejora

## NOTAS

- Actualizar este archivo marcando [x] las tareas completadas y [EN PROCESO] las que estén en curso.
- Las tareas completadas se irán marcando a medida que avancemos.
