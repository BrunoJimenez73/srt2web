# SRT2Web Helm Chart

Despliegue de SRT2Web en Kubernetes.

## Requisitos

- Kubernetes 1.22+
- Helm 3.8+
- PV provisioner (para persistencia de outputs)

## Instalación

```bash
# Desde el repo
helm install srt2web ./deploy/helm/srt2web

# Con valores personalizados
helm install srt2web ./deploy/helm/srt2web \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=srt2web.midominio.com \
  --set secrets.auth_token=mi-token-secreto
```

## Configuración

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `replicaCount` | `1` | Réplicas del deployment |
| `image.repository` | `ghcr.io/brunojimenez73/srt2web` | Imagen Docker |
| `image.tag` | `latest` | Tag de la imagen |
| `service.type` | `ClusterIP` | Tipo de servicio |
| `ingress.enabled` | `false` | Habilitar Ingress |
| `persistence.size` | `50Gi` | Tamaño del volumen persistente |
| `srt.port` | `9000` | Puerto SRT (UDP) |
| `autoscaling.enabled` | `false` | Auto-escalado horizontal |
| `resources.limits.cpu` | `4000m` | Límite de CPU |
| `resources.limits.memory` | `8Gi` | Límite de memoria |

## Probes

- **Liveness** (`/live`): 30s initial, cada 15s
- **Readiness** (`/ready`): 15s initial, cada 10s
- **Startup** (`/live`): 5s initial, 30 failures max (150s startup grace)
