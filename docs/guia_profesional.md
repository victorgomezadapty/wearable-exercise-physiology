# Guía para profesionales: qué puede y qué no puede decirte un wearable de muñeca sobre tu cliente

Para fisioterapeutas, entrenadores y preparadores físicos que usan wearables de muñeca (relojes inteligentes, pulseras de
investigación) con sus clientes o pacientes. Cada fila se apoya en un análisis de este repositorio: notebooks 02, 06, 07
y 08. Versión en inglés: [practitioner_guide.md](practitioner_guide.md).

> Base de la evidencia: 36 adultos jóvenes sanos, Empatica E4 en la muñeca, una sesión por condición (dataset de
> PhysioNet, Hongn et al. 2025). Los relojes comerciales usan otros algoritmos, pero se enfrentan a la misma física: la
> frecuencia cardiaca óptica en la muñeca y el movimiento. Úsala como guía de preguntas que conviene hacerse, no como
> recomendación clínica.

## ¿Me puedo fiar del dato?

| Situación | ¿Fiable? | Evidencia de este proyecto | Qué hacer en su lugar |
|---|---|---|---|
| **FC sentado y quieto** | ✅ En general | Válida en ~60–70 % de las ventanas de 30 s | Úsala, revisando los huecos |
| **FC pedaleando a ritmo constante** | ⚠️ A menudo no | Válida en el 43 % de las ventanas. En la última etapa, utilizable en **14 de 30** personas. Algunos valores "válidos" salen más bajos que en etapas más fáciles | Banda de pecho para decidir intensidades; contrastar con RPE |
| **FC en sprints / intervalos** | ❌ No | Válida en el **3 %** de las ventanas de sprint; 12 % en los 2 min posteriores | Banda de pecho, o valorar la recuperación ya en reposo |
| **VFC (RMSSD)** | Solo sentado | Durante el ejercicio el RMSSD del E4 se queda en 25–35 ms a ~130 lpm: es artefacto | Medir la VFC sentado o tumbado, quieto, con ≥ 60 latidos limpios consecutivos |
| **Actividad electrodérmica (EDA) como marcador de estrés** | Depende del contexto | Estrés ×1,6; pico de ejercicio **×11** (sudoración) | Interpretarla solo en reposo y frente a la propia línea base de la persona |
| **Temperatura de la piel** | ❌ No aporta | Sin cambios fiables en ninguna condición; ICC ≈ 0–0,3 | No usarla para decidir |
| **Movimiento / cadencia** | ✅ Sí | Coincide con la cadencia prescrita desde 85 rpm; detecta la quietud durante el estrés | Usarlo como contexto para interpretar todo lo demás |

## ¿Puedo tomar una decisión sobre esta persona?

| Pregunta | Respuesta corta | Evidencia | Regla práctica |
|---|---|---|---|
| **¿Este cliente "responde" al estrés?** | No con una sola prueba | El ruido de medida (error típico 2,4 lpm) ≈ el cambio mínimo relevante (2,3 lpm). Tras una tarea de estrés de 3–4 min, **19 de 34** personas quedan como dudosas en FC | Repetir la medición (~**6 veces** para FC, ~4 para EDA) y comparar con su propia línea base |
| **¿De verdad cada persona responde distinto?** | Sí, y mucho | DE de la respuesta individual real **7,6 lpm** alrededor de una media de +5 lpm. Aproximadamente 1 de cada 4 no sube realmente la FC | No aplicar nunca la media del grupo a un individuo |
| **¿Qué señal debo monitorizar?** | Más de una | Las respuestas de FC y EDA no están relacionadas (ρ ≈ −0,06). De 15 personas con respuesta clara, solo 3 responden en ambas | Vigilar un solo canal deja fuera a la mitad de los que responden |
| **¿Lo que dicen coincide con su fisiología?** | En parte | Dentro de cada persona, la FC sigue moderadamente el estrés percibido (r_rm = 0,40). Lo que reportan no predice *qué* canal responde; un participante respondió claramente en ambos sin notar ningún cambio | Preguntar *y* medir: uno no sustituye al otro |
| **¿La sesión alcanzó la intensidad buscada?** | Comprobarlo persona a persona | El mismo protocolo de cadencias terminó entre el **46 % y el 91 % de la FCmáx estimada** (de ligera a vigorosa) en las 14 personas medibles | Prescribir por carga interna (zonas de FC desde una FCmáx medida, RPE), no solo por carga externa |
| **¿Sirve 220 − edad o 208 − 0,7 × edad?** | Con cautela | Error individual ≈ ±10 lpm (≈ ±5 puntos porcentuales) | Usar una FCmáx medida cuando la decisión dependa de ella |
| **¿Me fío de un modelo que "detecta el estrés"?** | Pregunta cómo se validó | El mismo modelo obtiene macro-F1 **0,83** probado con ventanas de personas conocidas y **0,66** con personas nuevas | Fiarse solo de resultados validados en personas que el modelo nunca ha visto |

## Cinco reglas

1. **Antes de interpretar a la persona, comprueba si el wearable la puede medir.** Mira primero los huecos y el contexto
   de actividad.
2. **Compara a cada persona consigo misma.** Las líneas base varían tanto entre personas (ICC 0,83–0,99) que los umbrales
   poblacionales engañan.
3. **Una medición es una hipótesis, no un diagnóstico.** Repite antes de etiquetar a nadie.
4. **Carga externa no es carga interna.** Verifica la intensidad en cada persona.
5. **El movimiento explica mucho.** Muchas diferencias "fisiológicas" entre actividades son movimiento, o un sensor que
   falla con el movimiento.

## Límites

Adultos sanos de 18 a 31 años, un solo dispositivo, sesiones únicas, sin referencia de ECG ni VO₂. No aplicable a
poblaciones clínicas, a fármacos que alteran la FC (p. ej. betabloqueantes) ni al diagnóstico.
