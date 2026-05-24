# Load Testing Suite

Tests de carga para SRT2Web usando [Locust](https://locust.io/).

## Escenarios

| Escenario             | Descripción                         | Ratio               |
| --------------------- | ----------------------------------- | ------------------- |
| `DashboardMonitoring` | Cliente dashboard haciendo polling  | 3-5s entre requests |
| `PipelineControl`     | Operador iniciando/parando pipeline | 10-20s entre ops    |
| `MixedLoad`           | 70% lecturas + 30% escrituras       | 2-6s entre requests |

## Requisitos

```bash
pip install locust
```

## Uso básico

```bash
# Interfaz web (http://localhost:8089)
locust -f tests/load/locustfile.py --host=http://localhost:9999

# Headless: 10 usuarios, 2 por segundo, 60 segundos
locust -f tests/load/locustfile.py --host=http://localhost:9999 --headless -u 10 -r 2 --run-time 60s

# Solo un escenario específico
locust -f tests/load/locustfile.py --host=http://localhost:9999 DashboardMonitoring
```

## Ejecutar benchmark rápido

```bash
# 5 usuarios simulando dashboard por 30s
locust -f tests/load/locustfile.py --host=http://localhost:9999 --headless -u 5 -r 1 --run-time 30s --csv=results/quick
```

## Interpretación de resultados

Locust genera:

- **RPS** (Requests Per Second): throughput del servidor
- **Response Time (ms)**: P50, P95, P99 latencia
- **Failure Rate**: % de requests fallidos
- **Número de usuarios**: concurrentes simulados

### Objetivos de rendimiento

| Métrica             | Target  | Alerta |
| ------------------- | ------- | ------ |
| GET /api/status P95 | < 500ms | > 2s   |
| POST /api/start     | < 3s    | > 10s  |
| Failure rate        | < 1%    | > 5%   |
| RPS sostenido       | > 50    | < 10   |
