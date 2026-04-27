# Plan de Mejoras SRT2Web - Tareas

## FASE 1: ANÁLISIS DEL PROYECTO
- [x] Analizar estructura core/
- [x] Analizar estructura server/
- [x] Analizar estructura modules/
- [x] Analizar estructura frontend/
- [x] Verificar estado actual TypeScript (crear tsconfig.root.json)
- [EN PROCESO] Verificar estado mypy Python (ejecutar mypy --strict)
- [ ] Buscar strings literales y hardcodeos
- [ ] Revisar configuraciones de seguridad
- [ ] Revisar patrones de diseño y arquitectura

## FASE 2: SEGURIDAD
- [ ] Auditar middleware (Auth, RateLimit, SecurityHeaders)
- [ ] Implementar gestión de tokens vía variables de entorno
- [ ] Añadir pruebas unitarias de rate-limit y WS auth
- [ ] Verificar CSP y encabezados de seguridad
- [ ] Revisar sanitización de inputs en API y módulos
- [ ] Validar autenticación WebSocket

## FASE 3: ESCALABILIDAD
- [ ] Analizar pool de procesos FFmpeg (dinamizar)
- [ ] Exponer métricas de hardware y FFmpeg
- [ ] Revisar uso de memoria (MemoryManager)
- [ ] Optimizar ModelCache (TTL, pre-carga)
- [ ] Prototipo de cola (Redis) para pipeline distribuido
- [ ] Evaluar diseño para horizontal scaling (load balancer)

## FASE 4: MANTENIBILIDAD
- [ ] Eliminar valores por defecto en código (usar ConfigManager)
- [ ] Añadir docstrings y generar MkDocs
- [ ] Ejecutar linters (flake8, black, isort) en CI
- [ ] Habilitar mypy --strict y corregir errores
- [ ] Refactor de hard-code a constantes / env vars
- [ ] Mejorar cobertura de tests (unit, integración, carga)

## FASE 5: FRONTEND UI/UX
- [ ] Añadir atributos ARIA y foco visible a componentes
- [ ] Unificar estilos de tarjetas UI (Card base)
- [ ] Verificar responsividad en breakpoints Tailwind
- [ ] Centralizar gestión de estados (loading, error) en store global
- [ ] Revisar internacionalización (evitar strings hard-codeados)
- [ ] Ejecutar pruebas de accesibilidad con axe-core

## FASE 6: INFORME FINAL Y PLAN DE IMPLEMENTACIÓN
- [ ] Listar todos los problemas encontrados
- [ ] Priorizar por severidad y esfuerzo
- [ ] Crear roadmap de implementación (sprints)
- [ ] Estimar esfuerzo por cada mejora

## NOTAS
- Actualizar este archivo marcando [x] las tareas completadas y [EN PROCESO] las que estén en curso.
- Las tareas completadas se irán marcando a medida que avancemos.