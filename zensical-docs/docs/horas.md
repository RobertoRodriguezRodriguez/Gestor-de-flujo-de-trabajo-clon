---
icon: lucide/clock
---

# Horas

Este Gestor de Flujo de Trabajo incluye un sistema de registro de horas por tarea que permite controlar el tiempo dedicado y compararlo con el presupuesto del proyecto.

## Registrar horas

Desde el detalle de una tarea, en la sección **Registro de horas**:

1. Introduce las **horas** trabajadas.
2. Añade una **nota** describiendo el trabajo (opcional).
3. Selecciona la **fecha** del registro (por defecto, hoy).
4. Pulsa **Registrar**.

Cada registro queda vinculado al usuario que lo crea, la tarea y el proyecto.

## Resumen de horas del proyecto

La pestaña **Horas** del proyecto muestra:

### Resumen global

| Métrica | Descripción |
|---------|-------------|
| **Presupuesto** | Total de horas definido al crear el proyecto. |
| **Consumidas** | Suma de todas las horas registradas en el proyecto. |
| **Restantes** | `Presupuesto − Consumidas`. En rojo si es negativo. |
| **Uso (%)** | Porcentaje del presupuesto consumido. |

Una barra de progreso visualiza el uso:

- 🟢 Verde — Menos del 80 % consumido.
- 🟡 Amarillo — Entre el 80 % y el 100 %.
- 🔴 Rojo — Presupuesto superado.

### Desglose por miembro

Tabla con las horas totales registradas por cada miembro del proyecto.

### Desglose por tarea

Tabla con las horas registradas por tarea, incluyendo las horas estimadas y el estado de la tarea.

## Validación de horas

Las horas pueden requerir validación por parte del responsable del proyecto. El campo `hours_validated` de la tarea indica si las horas han sido validadas.

## Pool de horas de usuario

Cada usuario puede tener un `hours_pool` configurado en su perfil, que representa el total de horas disponibles en el sistema. Los managers pueden consultarlo desde la gestión de miembros.

!!! tip "Exportación"
    Los datos de horas pueden exportarse a Excel (`.xlsx`) desde la vista de administración gracias a la integración con `openpyxl`.
