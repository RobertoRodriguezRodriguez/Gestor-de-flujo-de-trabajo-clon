---
icon: lucide/bar-chart-2
---

# Analítica

El gestor proporciona varios gráficos para entender el estado y progreso del proyecto, todos renderizados en SVG directamente en el navegador sin dependencias externas.

## Distribución de tareas

La distribución de tareas está integrada en los **filtros del tablero**. Cada opción del filtro muestra el número de tareas que corresponde:

- **Filtro Asignado** → conteo de tareas por miembro (datos del servidor, top 10 por volumen).
- **Filtro Prioridad** → conteo de tareas por prioridad.
- **Filtro Sprint** → conteo de tareas por sprint.
- **Filtro Etiqueta** → conteo de tareas por etiqueta.

Esto permite identificar de un vistazo dónde está concentrado el trabajo. Pulsar cualquier opción aplica el filtro al tablero al instante.

## Gráfico de Velocidad

**Ubicación:** Pestaña Sprints → parte superior.

Muestra la cantidad de trabajo completado por sprint en forma de gráfico de barras.

```
 10 │  ████
  8 │  ████  ████
  6 │  ████  ████  ████
  4 │  ████  ████  ████  ░░░░
    └──────────────────────────
      Sp 1  Sp 2  Sp 3  Sp 4(activo)
             - - - Promedio - - -
```

**Eje Y:** número de tareas completadas o horas estimadas completadas.  
**Eje X:** sprints ordenados cronológicamente (máximo 8).  
**Línea discontinua:** promedio del equipo.

Usa el selector **Tareas / Horas est.** para cambiar la métrica. El selector de horas solo aparece si hay horas estimadas registradas.

## Gráfico de Burndown

**Ubicación:** Pestaña Sprints → debajo de cada sprint que tenga fechas definidas.

Compara el progreso esperado (línea ideal) con el real (tareas completadas por día).

| Elemento | Descripción |
|----------|-------------|
| Línea discontinua gris | Ritmo ideal: completar el mismo número de tareas cada día. |
| Línea sólida (accent) | Tareas restantes reales, calculadas por fecha de completado. |
| Área sombreada | Superficie bajo la curva real. |
| Punto final | Situación actual del sprint. |
| Línea vertical amarilla | Día de hoy (solo si el sprint está en curso). |

### Interpretación del ritmo

| Indicador | Situación |
|-----------|-----------|
| ✅ **Por delante** | El equipo va más rápido de lo planificado. |
| 🟡 **Al día** | El progreso sigue el plan. |
| 🔴 **Con retraso** | El equipo va más lento de lo planificado. |
| ✓ **Completado** | El sprint ha finalizado. |

!!! info "Cálculo del ritmo"
    El ritmo se calcula comparando las tareas restantes reales hoy con las que debería haber según la línea ideal. Una diferencia mayor de ±0,5 tareas cambia el estado.

## Datos y actualización

Todos los gráficos se calculan en el servidor en cada carga de página. No hay peticiones AJAX adicionales — los datos se inyectan como JSON en el HTML y se renderizan con SVG vanilla en el cliente.
