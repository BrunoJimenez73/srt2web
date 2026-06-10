# Helm Chart srt2web (archivado)

Helm chart para desplegar srt2web en Kubernetes. **Archivado el 2026-06-05
durante F110**.

## Por qué está archivado

El chart se desarrolló como parte de F51 (despliegue en Kubernetes) que
quedó en estado `pending` y nunca se completó. Razones:

1. **El proyecto no tiene un caso de uso claro para K8s.** srt2web es una
   aplicación de procesamiento de streams en tiempo real con dependencias
   pesadas (Whisper, Piper TTS, FFmpeg con GPU). El caso de uso principal
   es un主播 individual con OBS Studio en una sola máquina, no un cluster.

2. **Latencia de red añade jitter inaceptable** para subtitulado en vivo.
   Los 12-15s de latencia del pipeline se degradan en K8s por encapsulación
   de red y scheduling de pods.

3. **GPU passthrough en K8s es complejo** y no compensa para una sola
   instancia. El chart usaba `passthrough` encoder, lo que evita el problema,
   pero entonces la ventaja de GPU desaparece.

4. **El chart nunca se probó con un cluster real.** Solo se validó la
   sintaxis con `helm template` y `helm lint`. No hay tests de integración
   contra un cluster.

## Si necesitas desplegar en K8s en el futuro

El chart sigue siendo funcional y la estructura es estándar. Para activarlo:

1. Mover `chart/` de vuelta a `deploy/helm/srt2web/`.
2. Crear un Container Registry y publicar imágenes con `frontend/Containerfile`.
3. Configurar un PV provisioner (NFS, EBS, Longhorn) para el `PersistentVolumeClaim`.
4. Probar con `helm install srt2web ./deploy/helm/srt2web --dry-run` en un
   cluster de desarrollo antes de producción.

## Contenido del chart

```
chart/
├── Chart.yaml          # Metadata: name=srt2web, version=0.6.8
├── values.yaml         # Configuración por defecto
├── README.md           # Documentación original del chart
├── .helmignore
└── templates/
    ├── _helpers.tpl    # Template helpers
    ├── configmap.yaml  # config.yaml montado como ConfigMap
    ├── deployment.yaml # Deployment con health probes
    ├── hpa.yaml        # HorizontalPodAutoscaler (deshabilitado por defecto)
    ├── ingress.yaml    # Ingress (deshabilitado por defecto)
    ├── NOTES.txt       # Mensaje post-install
    ├── pvc.yaml        # PersistentVolumeClaim para output/
    ├── secrets.yaml    # AUTH_TOKEN, SECRET_KEY
    └── service.yaml    # Service ClusterIP
```

## Mantenimiento

**No actualizar.** Este chart está congelado en `appVersion: 0.6.8`. Si en
el futuro se reactiva el despliegue en K8s, partir de cero sería más rápido
que actualizar este chart al estado actual del proyecto.
