import type { Messages } from "./en";

// Spanish.
const messages: Messages = {
  // ---------------------------------------------------------------- shared
  "language.label": "Idioma",
  "app.title": "Rutas ante inundaciones en Southbank",
  "unit.min": "{count} min",
  "depth.unknown": "desconocida",
  "depth.none": "ninguna",
  "depth.withLabel": "{depth} ({label})",
  "route.recommended": "Recomendada",
  "route.safe_shortest": "La más corta dentro de su límite",
  "route.shortest": "La más corta, sin tener en cuenta la inundación",
  "route.downgrade": "Con un límite más alto",
  "route.refuge": "Hacia un refugio",
  "route.least_water": "Menos agua",
  "error.unreachable": "No se puede conectar con el servicio de rutas. Revise su conexión e inténtelo de nuevo.",
  "error.status": "El servicio de rutas devolvió un error ({status}).",

  // ---------------------------------------------------------------- the app: panel
  "app.tagline": "Rutas a pie que evitan el agua más profunda de lo que usted decide atravesar caminando.",
  "app.panel": "Planificador de trayectos",
  "app.sheetMore": "Mostrar más mapa",
  "app.sheetDetails": "Mostrar detalles",
  "app.loadError": "No se pudieron cargar los datos del mapa.",
  "app.planError": "No se pudo planificar este trayecto.",
  "app.planning": "Planificando…",
  "app.safety":
    "Las rutas son orientativas y se basan en condiciones modeladas, que pueden ser incompletas o erróneas, y las inundaciones cambian rápido. Nunca camine por agua de inundación si no es imprescindible, siga las indicaciones de los servicios de emergencia y, en una emergencia, llame al 000 (VICSES 132 500 para ayuda por inundación o tormenta).",
  "app.credits": "Datos del mapa © colaboradores de OpenStreetMap. Escenarios de inundación: vea Fuentes en cada nivel.",
  "app.nextClick": "El siguiente clic marca el {target}",
  "app.nextClick.start": "inicio",
  "app.nextClick.destination": "destino",

  "trip.label": "Inicio y destino",
  "trip.start": "Inicio",
  "trip.destination": "Destino",
  "trip.locate": "Usar mi ubicación actual",
  "trip.swap": "Intercambiar",
  "trip.clear": "Borrar",
  "trip.hint": "Busque un lugar o haga clic en el mapa: el primer clic marca el inicio y el siguiente, el destino.",
  "trip.outside": "Elija un punto dentro de Southbank (el contorno negro).",
  "trip.placeOutside": "{place} está fuera de Southbank.",
  "trip.noGeolocation": "La ubicación no está disponible en este navegador. Haga clic en el mapa para marcar su inicio.",
  "trip.locating": "Buscando su ubicación…",
  "trip.locationOutside": "Su ubicación está fuera de Southbank. Haga clic en el mapa para marcar una ubicación actual simulada.",
  "trip.locationFailed": "Ubicación no disponible (permiso denegado o función no compatible). Haga clic en el mapa para marcar su inicio.",
  "trip.yourLocation": "Su ubicación",
  "trip.pointOnMap": "Punto en el mapa",
  "trip.pointAt": "{place} ({lat}, {lon})",

  "search.onMap": "Marcar en el mapa",
  "search.onMapActive": "El siguiente clic en el mapa marca este punto",
  "search.change": "Cambiar",
  "search.placeholder": "p. ej., Eureka Tower, 1 City Road",
  "search.button": "Buscar",
  "search.tooShort": "Escriba al menos tres letras.",
  "search.failed": "La búsqueda falló.",
  "search.noMatch": "No hay resultados dentro de Southbank. Pruebe con otro nombre o haga clic en el mapa.",

  // ---------------------------------------------------------------- flood conditions
  "conditions.title": "Condiciones de inundación",
  "conditions.group": "Escenario de inundación",
  "conditions.none": "Ninguna",
  "conditions.over": "más de {depth}",
  "conditions.water":
    "Agua {range} ({band} para un adulto de {height} cm). Profundidad típica en las aceras inundadas de esta zona: {depth}.",
  "conditions.dry": "No hay agua estancada.",
  "conditions.sources": "Fuentes",

  // ---------------------------------------------------------------- the traveller
  "you.title": "Usted",
  "you.height": "Estatura",
  "you.aid": "Ayuda para la movilidad",
  "you.aidNone": "Ninguna",
  "you.aidDepth": "Profundidad máxima del agua para su {aid}",
  "you.aidNote":
    "Los límites para ayudas con ruedas dependen del dispositivo (eje de la rueda giratoria delantera, chasis, indicaciones del fabricante), no de su estatura. Las rutas nunca usan escalones ni aceras medidas con más pendiente que 1:14.",
  "you.wading": "Profundidad máxima del agua por la que caminará",
  "you.limit": "Su límite: {limit}",
  "you.cap": "(nunca más de {cap})",
  "you.preference": "Preferencia de ruta",
  "you.preferenceNote":
    "El agua más profunda que su límite siempre se evita; esto solo decide si vale la pena rodear el agua que está dentro de su límite.",
  "you.advanced": "Avanzado",
  "you.alpha": "Peso del riesgo α: {alpha}",
  "you.alphaNote": "Metros adicionales que vale la pena caminar para evitar un metro de agua justo en su límite.",
  "you.alphaBack": "Volver a la preferencia",

  // ---------------------------------------------------------------- trip results
  "origin.unknownWater": "agua de profundidad desconocida",
  "origin.water": "{depth} de agua",
  "origin.overLimit": "Se encuentra en {water} ({label}), por encima de su límite.",
  "origin.deep": "Se encuentra en {water} ({label}). Muévase con cuidado; hay ayuda disponible.",
  "origin.veryDeep": "Profundidad del agua aquí: {depth}, por encima de su rodilla. Se recomienda pedir ayuda antes de moverse.",
  "origin.criticalUnknown": "No se conoce la profundidad del agua aquí.",
  "origin.critical": "Profundidad del agua aquí: {depth} ({label}).",
  "origin.criticalAction": "Quédese donde está si puede y llame ahora para pedir ayuda.",

  "emergency.title": "Ayuda de emergencia — {advice}",
  "emergency.available": "disponible",
  "emergency.recommended": "recomendada",
  "emergency.stronglyRecommended": "muy recomendada",
  "emergency.onlyOption": "su única opción",
  "emergency.cutOff": "El agua profunda le impide salir. Quédese adentro y, si entra agua en el edificio, suba a un piso más alto.",
  "emergency.note": "000 si la vida de alguien corre peligro; VICSES para ayuda por inundación, por ejemplo si el agua no le deja salir o si entra agua.",

  "compare.title": "Comparar rutas",
  "compare.notSafe": "no es segura",
  "compare.deepest": "Profundidad máxima: {depth} · {water} en el agua",
  "compare.overLimit": "{count} tramo(s) por encima de su límite",
  "compare.hint": "Seleccione una ruta para verla en el mapa.",
  "compare.blocked": "En este escenario, {count} tramos de la red están por encima de su límite.",
  "access.avoidsSteps": "Todas las rutas evitan los escalones del camino más corto.",
  "access.avoidsSteep": "Todas las rutas evitan los tramos con más pendiente que 1:14 del camino más corto.",
  "access.avoidsBoth": "Todas las rutas evitan los escalones y los tramos con más pendiente que 1:14 del camino más corto.",
  "access.stepFree": "Ninguna ruta tiene escalones.",
  "gradient.none": "Sin datos de pendiente",
  "gradient.one": "Pendiente {gradient}",
  "gradient.range": "Pendiente de {from} a {to}",
  "trip.fromTo": "Desde {from} hasta {to}.",
  "trip.selectedPoint": "el punto seleccionado",
  "trip.placeAccess": "{place} ({access})",

  // ---------------------------------------------------------------- the next step card
  "next.label": "Siguiente paso",
  "next.go": "Puede ir: esta ruta se mantiene dentro de su límite",
  "next.detour": "Tome la ruta recomendada",
  "next.choose": "Ninguna ruta se mantiene dentro de su límite. Elija una:",
  "next.downgrade": "Ninguna ruta se mantiene dentro de su límite",
  "next.shelterCritical": "Quédese donde está si puede y llame para pedir ayuda",
  "next.shelterFold": "Si no puede esperar a que llegue ayuda: el camino a un refugio",
  "next.shelter": "Vaya a un refugio y espere",
  "next.stay": "Quédese dentro de {place} hasta que baje el agua",
  "next.help": "No hay una salida segura desde aquí: llame para pedir ayuda",
  "next.helpBody": "No se puede llegar a ningún refugio. Quédese en el lugar más alto al que pueda llegar.",
  "next.unreachable": "Ninguna ruta conecta estos puntos",
  "next.show": "Mostrar en el mapa",
  "next.shown": "Visible en el mapa",
  "next.accept": "Aceptar {water} ({depth})",
  "next.useLimit": "Usar este límite",
  "next.refuge": "Espere en un refugio: {name}",
  "next.refugeWay": "Acceso: {entrance}. Recorrido: {route}. Espere allí hasta que baje el agua.",
  "next.refugeOverLimit": "El camino hasta allí cruza agua más profunda que su límite; es la salida menos profunda.",
  "next.stayInside": "Quédese dentro de {place}",
  "next.wait": "Espere hasta que baje el agua.",
  "next.leastWater": "El camino con menos agua",
  "next.routeLine": "{distance} · {time} · profundidad máxima: {depth}",
  "metric.walk": "a pie",
  "metric.vsShortest": "+{percent}% respecto a la más corta",
  "metric.estimated": "estimado",
  "metric.unknown": "Desconocida",
  "metric.dry": "Seco",
  "metric.deepest": "profundidad máxima",
  "metric.inWater": "en el agua",
  "metric.steepest": "pendiente máxima",
  "metric.gentlest": "pendiente mínima",
  "metric.noGradient": "sin datos de pendiente",

  "why.unknown": "Todos los caminos hasta allí cruzan agua de profundidad desconocida.",
  "why.unknownTo": "Todos los caminos hasta {place} cruzan agua de profundidad desconocida.",
  "why.overLimit":
    "Todos los caminos hasta allí cruzan al menos {depth} de agua ({label}), más que su límite de {limit}. El punto más profundo está marcado en el mapa.",
  "why.overLimitTo":
    "Todos los caminos hasta {place} cruzan al menos {depth} de agua ({label}), más que su límite de {limit}. El punto más profundo está marcado en el mapa.",
  "why.overCap":
    "Todos los caminos hasta allí cruzan al menos {depth} de agua ({label}), más que el límite máximo de {limit} que se aplica a todas las personas. El punto más profundo está marcado en el mapa.",
  "why.overCapTo":
    "Todos los caminos hasta {place} cruzan al menos {depth} de agua ({label}), más que el límite máximo de {limit} que se aplica a todas las personas. El punto más profundo está marcado en el mapa.",
  "why.overAidCap":
    "Todos los caminos hasta allí cruzan al menos {depth} de agua ({label}), más que el límite máximo de {limit} que se aplica a usuarios de {aid}. El punto más profundo está marcado en el mapa.",
  "why.overAidCapTo":
    "Todos los caminos hasta {place} cruzan al menos {depth} de agua ({label}), más que el límite máximo de {limit} que se aplica a usuarios de {aid}. El punto más profundo está marcado en el mapa.",
  "detour.unknown":
    "El camino más corto ({distance}) cruza agua de profundidad desconocida. Esta ruta recorre {extra} más para mantenerse dentro de su límite.",
  "detour.overLimit":
    "El camino más corto ({distance}) cruza agua más profunda que su límite, de hasta {depth} ({label}). Esta ruta recorre {extra} más para mantenerse dentro de su límite.",
  "detour.avoid": "Esta ruta recorre {extra} más que el camino más corto para evitar {water} de agua de hasta {depth} ({label}).",

  // ---------------------------------------------------------------- map and legend
  "map.label": "Mapa de Southbank",
  "map.unknownDepth": "Profundidad desconocida · se considera demasiado profunda",
  "map.overLimit": "por encima de su límite",
  "map.shelter": "Refugio: {name}",
  "map.deepest": "Punto más profundo de la ruta con menos agua: {depth}",
  "map.deepestUnknown": "Punto más profundo de la ruta con menos agua: profundidad desconocida",
  "map.failed": "El mapa dejó de dibujarse.",
  "map.failedWhy": "El navegador se quedó sin recursos gráficos.",
  "map.reload": "Recargar mapa",
  "map.failedNote": "Si esto sigue pasando, cierre el navegador y vuelva a abrirlo.",
  "map.zoomIn": "Acercar",
  "map.zoomOut": "Alejar",
  "map.attribution": "Mostrar u ocultar la atribución",
  "legend.title": "Leyenda",
  "legend.waterOk": "Agua dentro de su límite",
  "legend.waterOver": "Por encima de su límite o de profundidad desconocida",
  "legend.shortestUnsafe": "La más corta, sin tener en cuenta la inundación (no es segura)",
  "legend.downgradeBody": "Con límite: {label}",
  "legend.downgradeAid": "Con un límite más alto ({depth})",
  "legend.deepest": "Punto más profundo de la ruta con menos agua",

  // ---------------------------------------------------------------- getting help
  "help.button": "Pedir ayuda",
  "help.close": "Cerrar",
  "help.call000": "Llamar al 000",
  "help.lifeDanger": "Si la vida de alguien corre peligro.",
  "help.ses": "Ayuda por inundación o tormenta: si el agua no le deja salir, si entra agua o si cayó un árbol.",
  "help.simulated": "Las llamadas abren el marcador de su teléfono. En esta versión, la alerta SOS es simulada.",
  "sos.button": "Alertar a las personas cercanas (SOS)",
  "sos.sent": "SOS enviado hace {seconds} s con {shared} (simulado).",
  "sos.undo": "Deshacer ({seconds} s)",
  "sos.noLocation": "sin ubicación (marque un inicio para compartirla)",
  "sos.currentLocation": "su ubicación actual",
  "sos.startAsLocation": "su punto de inicio como ubicación",
  "sos.here": "su ubicación",
  "sos.hereWithDepth": "su ubicación y {depth} de profundidad del agua",

  // ---------------------------------------------------------------- shared by /reference and /benchmark
  "doc.back": "← Rutas ante inundaciones en Southbank",
  "doc.sections": "Secciones",
  "basis.cited": "Citado",
  "basis.derived": "Derivado",
  "basis.chosen": "Criterio",
  "basis.chosenTitle": "Un valor elegido por criterio propio",

  // ---------------------------------------------------------------- /reference
  "ref.title": "Fuentes y referencias",
  "ref.pageTitle": "Fuentes y referencias · Rutas ante inundaciones en Southbank",
  "ref.intro":
    "De dónde vienen el mapa, la red y los escenarios de inundación, y en qué se basa cada límite de profundidad. Los valores de las tablas se leen del sistema en funcionamiento, así que son los que usan las rutas.",
  "ref.nav.data": "Datos",
  "ref.nav.scenarios": "Escenarios de inundación",
  "ref.nav.limits": "Límites de profundidad",
  "ref.nav.documents": "Documentos",
  "ref.nav.licences": "Licencias",
  "ref.nav.notCovered": "Lo que no cubre",
  "ref.data.title": "Datos",
  "ref.data.data": "Datos",
  "ref.data.use": "Uso",
  "ref.data.licence": "Licencia",
  "ref.scenarios.title": "Escenarios de inundación",
  "ref.scenarios.intro":
    "Cada escenario es un nivel de agua publicado aplicado al modelo del terreno: el río y la marea de tormenta, los desagües que rebosan con la marea alta y la lluvia que se acumula en las zonas bajas. Su nivel de inundación lo determina la profundidad típica en las aceras inundadas.",
  "ref.scenarios.typical": "profundidad típica {depth}",
  "ref.limits.title": "Límites de profundidad",
  "ref.limits.cited": "tomado de una fuente identificada.",
  "ref.limits.derived": "calculado a partir de valores citados.",
  "ref.limits.chosen": "ninguna fuente fija el valor, así que se elige; son los primeros que se revisarán cuando haya mejor evidencia.",
  "ref.loading": "Cargando los valores actuales…",
  "ref.loadError": "No se pudieron cargar los valores actuales: {error}",
  "ref.walking": "A pie",
  "ref.walkingIntro":
    "Quienes caminan eligen como una parte del cuerpo la profundidad máxima del agua por la que caminarán; esa parte se convierte en una profundidad según su estatura. Las profundidades de abajo corresponden a un adulto de {height} cm.",
  "ref.choice": "Opción",
  "ref.depth": "Profundidad",
  "ref.basis": "Fundamento",
  "ref.fraction": "({fraction} × estatura)",
  "ref.upperLimit": "Límite máximo para todas las personas",
  "ref.atMost": "como máximo {depth}",
  "ref.aids": "Sillas de ruedas y scooters de movilidad",
  "ref.aidsIntro":
    "Quienes usan una ayuda para la movilidad con ruedas eligen, en cambio, un nivel de su dispositivo, y las rutas nunca les llevan por escalones ni por caminos con más pendiente que 1:14, la rampa más empinada que permite AS 1428.1. Cada ruta muestra su pendiente medida máxima y mínima.",
  "ref.deviceLevel": "Dispositivo y nivel",
  "ref.cap": "(límite máximo)",
  "ref.levels": "Niveles de inundación",
  "ref.levelsIntro":
    "Los cuatro niveles se nombran según hasta dónde llega el agua típica en un adulto de {height} cm: las líneas de agua del tobillo, la rodilla y la cadera que se usan para clasificar la gravedad de una inundación (Feng, Brenner & Sester, 2020), con las alturas del cuerpo de Drillis & Contini (1966).",
  "ref.level": "Nivel",
  "ref.typicalWater": "Agua típica",
  "ref.over": "más de {depth}",
  "ref.seeParameters": "Vea docs/parameters.md",
  "ref.documents.title": "Documentos",
  "ref.documents.flooding": "Inundaciones en Southbank",
  "ref.documents.people": "Personas en agua de inundación y accesibilidad",
  "ref.documents.mobility": "Sillas de ruedas y scooters de movilidad",
  "ref.documents.note": "Las citas se dan en su idioma original.",

  "ref.licences.title": "Licencias",
  "ref.licences.software": "El software se distribuye bajo la {licence}.",
  "ref.licences.osm":
    "Los datos derivados de OpenStreetMap, como la red peatonal procesada, están disponibles bajo la {licence} y llevan el crédito © colaboradores de OpenStreetMap.",
  "ref.licences.others": "Los demás conjuntos de datos mantienen las licencias indicadas arriba. Los documentos se citan, no se redistribuyen.",
  "ref.notCovered.title": "Lo que no cubre",
  "ref.notCovered.notice":
    "Este no es un servicio oficial de alertas de inundación. Siga las alertas de VICSES y del Bureau of Meteorology, llame al 000 en una emergencia y llame a VICSES al 132 500 para pedir ayuda por inundación o tormenta.",
  "ref.footer": "Cada parámetro, dónde se define y por qué: {parameters}. Cómo funciona el sistema: {architecture}.",

  "ref.data.osm.name": "Red peatonal, edificios y entradas",
  "ref.data.osm.use": "Los caminos que siguen las rutas, los escalones, los edificios que se usan como inicio, destino y refugio, y sus entradas.",
  "ref.data.clue.use": "El contorno de Southbank, la zona que cubre el sistema.",
  "ref.data.pits.use": "Bocas de desagüe abiertas a la superficie, por donde la marea alta sube a través de los desagües.",
  "ref.data.steepness.use":
    "La pendiente de cada tramo de acera municipal: cada ruta muestra su pendiente medida máxima y mínima, y las rutas para sillas de ruedas y scooters excluyen los caminos con más pendiente que 1:14.",
  "ref.data.pedestrian.use": "Una red peatonal alternativa, que se usa para verificar la de OpenStreetMap.",
  "ref.data.dem.use": "La altura del terreno, a partir de la cual se calcula la profundidad del agua en cada punto.",
  "ref.data.overlays.use":
    "Terrenos que se espera que se inunden en un evento de 1 en 100 años; se muestran como contexto en la aplicación Streamlit y no se usan para las rutas.",
  "ref.data.search.name": "Búsqueda de lugares",
  "ref.data.search.use": "Encontrar un lugar escrito en los cuadros de búsqueda.",
  "ref.data.basemap.name": "Mapa base",
  "ref.data.basemap.use": "El mapa que se dibuja debajo de las rutas; si no carga, se usan los mosaicos propios de OpenStreetMap.",
  "ref.data.census.use":
    "Los idiomas en que se ofrece este sitio: los más hablados en casa en Southbank (SAL22315) y Southbank (West) – South Wharf (SA2 206041508).",

  "ref.doc.melbourneWater.use":
    "Cómo se inunda Southbank (marea de tormenta y caudales del río, aguas pluviales locales, desagües que no pueden descargar con la marea alta); 500 mm como acceso peatonal seguro, 300 mm para usos vulnerables.",
  "ref.doc.ghd.use":
    "Niveles de marea de tormenta en Port Phillip Bay (tabla 1): 1 en 20 años, 1.25 m; 1 en 100 años, 1.60 m; 1 en 100 años en 2100, 2.40 m AHD.",
  "ref.doc.waterTechnology.use": "Marea astronómica más alta en Williamstown, 0.59 m AHD (tabla 2-1): el nivel de inundación leve.",
  "ref.doc.floodSubPlan.use": "La marea alta reduce la capacidad de los desagües y el reflujo desborda alrededor de las bocas de desagüe.",
  "ref.doc.floodGuide.use":
    "Calles que se espera que se inunden según el medidor de nivel de Southbank, usadas para verificar los escenarios; el nivel de inundación mayor de ese medidor.",
  "ref.doc.vpp.use": "Planificación para 0.8 m de aumento del nivel del mar hacia 2100: el nivel de inundación extrema.",
  "ref.doc.drillis.use": "Alturas del tobillo, la rodilla y la cadera como fracciones de la estatura de una persona.",
  "ref.doc.feng.use":
    "El tobillo, la rodilla y la cadera como las líneas de agua que clasifican la gravedad de una inundación: los umbrales de los cuatro niveles de inundación.",
  "ref.doc.smith.use":
    "0.5 m como límite de profundidad para personas (H2) y límite para que niños caminen por el agua; las personas vulnerables deben evitar el agua de inundación en movimiento.",
  "ref.doc.abs.use": "Estatura media de un adulto, 1.69 m: el adulto de referencia de 1.70 m que se usa para describir los niveles de inundación.",
  "ref.doc.as1428.use":
    "Un recorrido accesible no tiene escalones ni rampas con más pendiente que 1:14 (rampas de bordillo de hasta 1:8 en 1.52 m), así que las rutas para sillas de ruedas y scooters no usan ninguno de los dos.",
  "ref.doc.minniemobil.use": "No cruzar agua de más de 2.5 cm de profundidad: el límite del scooter de movilidad.",
  "ref.doc.pride.use": "3.5 cm de altura libre sobre el suelo en el motor de un scooter de viaje.",
  "ref.doc.prideManuals.use": "Evitar el agua estancada; no subir bordillos de más de 5 cm.",
  "ref.doc.nitrum.use":
    "Ruedas giratorias delanteras de 3 a 6 pulgadas; el eje de una rueda giratoria está a la mitad de su diámetro (5.1 cm para 4 pulgadas, 7.6 cm para 6 pulgadas).",
  "ref.doc.q500.use": "3 pulgadas (7.6 cm) de altura libre sobre el suelo en una silla de ruedas eléctrica.",
  "ref.doc.permobil.use": "Unos 75 mm de altura libre sobre el suelo en una silla de ruedas eléctrica.",
  "ref.doc.invacare.use":
    "Componentes eléctricos probados según IPX4 (EN 60529): salpicaduras de agua, no inmersión. Estabilidad dinámica de 6° (10.5%) según ISO 7176-2: más que 1:14, que de todos modos se aplica a las sillas eléctricas (una decisión por criterio propio).",

  "ref.basis.no_wading": "Una película de agua que cualquier pavimento tiene cuando llueve; el agua más profunda ya cuenta como caminar por el agua.",
  "ref.basis.ankle": "0.039 × estatura (Drillis & Contini, 1966).",
  "ref.basis.lower_calf": "Un tercio de la distancia entre el tobillo y la rodilla.",
  "ref.basis.mid_calf": "A medio camino entre el tobillo y la rodilla.",
  "ref.basis.knee": "0.285 × estatura (Drillis & Contini, 1966); como máximo 50 cm.",
  "ref.basis.manualNoWater":
    "La misma tolerancia de pavimento seco que para quienes caminan; los fabricantes aconsejan evitar el agua estancada.",
  "ref.basis.castorAxle":
    "Eje de una rueda giratoria delantera de 4 pulgadas (5.1 cm); también el límite de bordillo de 5 cm de los manuales de Pride.",
  "ref.basis.largeCastorAxle":
    "Eje de una rueda giratoria de 6 pulgadas (7.6 cm). Ninguna fuente fija una profundidad de agua transitable para una silla de ruedas manual.",
  "ref.basis.sameAsWalkers": "La misma tolerancia de pavimento seco que para quienes caminan.",
  "ref.basis.belowChassis":
    "2.5 cm por debajo de unos 7.5 cm de altura libre sobre el suelo, con componentes eléctricos aptos solo para salpicaduras; el margen es una decisión por criterio propio.",
  "ref.basis.shallowPuddle":
    "La única profundidad que indica un fabricante (MinnieMobil); por debajo de los 3.5 cm de altura libre del motor de un scooter de viaje.",
  "ref.basis.hardLimit":
    "El plan de Melbourne Water para Southbank considera acceso peatonal seguro hasta 500 mm, y 0.5 m es el límite de profundidad H2 para personas (Smith, Davey & Cox, 2014). No se ofrecen el muslo ni la cintura: para casi todas las personas quedarían limitados a 50 cm.",
  "ref.basis.aidCap":
    "Ningún estudio mide qué tan estable es una silla de ruedas o un scooter ocupados en agua de inundación, por lo que los niveles siguen a los dispositivos y a sus fabricantes, muy por debajo de los 50 cm para quienes caminan.",

  "ref.limit.static":
    "Los escenarios de inundación son una estimación estática a partir de la altura del terreno y de niveles de agua publicados, no un modelo hidráulico: no tienen en cuenta el flujo, la velocidad, la evolución en el tiempo ni la capacidad de los desagües.",
  "ref.limit.surcharge":
    "No se tiene en cuenta el desborde de los desagües causado por la lluvia con marea normal, porque no se publican los niveles de las bocas de desagüe ni de las tuberías; una tormenta corta puede dejar agua más profunda que la que muestra el escenario de inundación leve.",
  "ref.limit.river":
    "Los niveles del río son los niveles de marea de la bahía; los caudales del río pueden elevarlos, así que las profundidades en el río son un valor mínimo.",
  "ref.limit.shelters": "Todo edificio con una entrada cuenta como refugio; los datos no indican si está abierto al público.",
  "ref.limit.gradients":
    "Las pendientes solo se conocen donde la City of Melbourne ha medido la acera (cerca de dos tercios de la longitud de aceras en Southbank); un camino sin medición, como una calzada o un camino privado, no se trata como empinado, y la pendiente máxima y mínima de una ruta solo cubren sus partes medidas.",
  "ref.limit.sections":
    "La pendiente de un tramo de acera es un promedio entre sus puntos más bajo y más alto, así que una parte corta y empinada de un tramo largo puede pasar desapercibida; se excluyen los tramos que parecen unir dos niveles (en puentes y pasos elevados).",

  // ---------------------------------------------------------------- /benchmark
  "bench.title": "Pruebas comparativas",
  "bench.pageTitle": "Pruebas comparativas · Rutas ante inundaciones en Southbank",
  "bench.intro":
    "Comprobación automática de si las rutas cumplen sus reglas con los datos que reciben, con datos inventados (un pequeño pueblo de prueba) y con la red real de Southbank. Las predicciones se escribieron antes de la primera ejecución, en {benchmarks}.",
  "bench.run": "Ejecutado el {date} en el commit {commit}; red de {nodes} cruces y {edges} tramos.",
  "bench.unknownCommit": "desconocido",
  "bench.loadError": "No se pudieron cargar los resultados de las pruebas: {error}",
  "bench.loading": "Cargando los resultados…",
  "bench.footer": "Vuelva a ejecutarlas con {command} en {folder}; los resultados se escriben en {file}.",
  "bench.measured": "Medido",
  "bench.asPredicted": "Según lo previsto",
  "bench.notAsPredicted": "No según lo previsto",
  "bench.share": "{count} de {total}",
  "bench.none": "ninguno",
  "bench.yes": "Sí",
  "bench.no": "No",
  "bench.algorithm": "Capa del algoritmo",
  "bench.correctness": "Corrección",
  "bench.pathFinder": "Buscador de caminos frente a NetworkX",
  "bench.pathFinderText":
    "De nodo a nodo: el mismo costo para {pairs} pares aleatorios ({same} con exactamente el mismo camino). A través del enrutador, con ajuste a la red y tramos de acceso: la misma longitud para {routes} trayectos aleatorios.",
  "bench.minimax": "Búsqueda del camino más seguro frente a fuerza bruta",
  "bench.minimaxText":
    "El punto más profundo más bajo posible, y luego el camino más corto con esa profundidad, coincidieron con la enumeración de todos los caminos para {pairs} pares de nodos en {graphs} grafos aleatorios.",
  "bench.predictions": "Predicciones derivadas a mano",
  "bench.predictionsText": "Casos del pueblo de prueba A–J: {town} cumplidos. Propiedades de Southbank R-A a R-I: {southbank} cumplidas.",
  "bench.faults": "Inyección de fallos",
  "bench.faultsText":
    "Cada fallo rompe a propósito una regla de seguridad; luego se ejecuta todo el conjunto de pruebas contra el código roto. Sin modificaciones, el conjunto tiene {failed} pruebas fallidas de {tests}.",
  "bench.fault": "Fallo",
  "bench.testsFailed": "Pruebas fallidas",
  "bench.casesFailed": "Casos fallidos del pueblo de prueba",
  "bench.caught": "Detectado",
  "bench.safety": "Seguridad peatonal",
  "bench.cost": "La seguridad y su costo",
  "bench.costText":
    "{trips} trayectos aleatorios en cada nivel de inundación. Ninguna ruta recomendada cruzó agua por encima del límite de la persona en {plans} planes{overLimit}. Cuando el camino más corto sin más cruza agua por encima del límite, la ruta recomendada es más larga en la mediana indicada y evita la longitud mediana de agua por encima del límite.",
  "bench.costOverLimit": " ({count} sí lo hicieron)",
  "bench.levelTraveller": "Nivel y persona",
  "bench.withRoute": "Ruta dentro del límite",
  "bench.shortestUnsafe": "Camino más corto inseguro",
  "bench.longerBy": "Más larga en",
  "bench.avoided": "Agua evitada por encima del límite",
  "bench.offered": "Sin ruta, se ofreció",
  "bench.rising": "Inundación en aumento: cambio de ruta en el camino",
  "bench.risingText":
    "{trips} trayectos de una persona ({traveller}) que camina mientras sube la inundación: {schedule}. En cada subida, el trayecto se vuelve a planificar desde donde está.",
  "bench.risingFrom": "{level} a partir de {minutes} min",
  "bench.risingViolations": "Agua por encima del límite recorrida en una ruta indicada como dentro de él: {metres}.",
  "bench.risingReroutes":
    "Cambió de ruta {reroutes} veces, en {trips} trayectos; {caught} veces el agua había subido por encima del límite donde estaba la persona, y la salida más segura cruzó {metres} de esa agua en total.",
  "bench.risingOutcomes": "Resultados: {outcomes}.",
  "bench.risingExtra": "Quienes llegaron caminaron {median} más de lo planificado al principio (mediana; percentil 90: {p90}).",
  "bench.finding": "Hallazgo:",
  "bench.findingText":
    "{count} veces la inundación subió mientras la ruta pasaba por el margen de la red fuera de Southbank, donde no se puede planificar ningún trayecto (el inicio debe estar dentro). La persona siguió la ruta que tenía y caminó allí {metres} por encima del límite en total. La replanificación debería funcionar desde cualquier punto de la red por el que pueda pasar una ruta.",
  "bench.access": "Accesibilidad del espacio público",
  "bench.stepFree": "Conectividad sin escalones entre edificios",
  "bench.stepFreeText":
    "{pairs} pares aleatorios de edificios conectados a pie, en condiciones normales. La ruta sin escalones también excluye los caminos con más pendiente que 1:14, que usan {steep} de las rutas a pie. Existe una ruta sin escalones para {routes}, y para {same} es la misma ruta a pie (sin escalones ni caminos empinados en el trayecto). Sobre todos los pares, es más larga en {median} en la mediana, {p90} en el percentil 90 y {max} como máximo. Ninguna ruta sin escalones usa escalones ({steps}) ni un camino con más pendiente que 1:14 ({steepUsed}), ni cuesta menos que la ruta a pie ({cheaper}).",
  "bench.stepFreeShorter.one":
    "{count} es más corta en metros pero cuesta más: las rutas minimizan el costo de caminar, y una calzada cuenta como tres veces su longitud.",
  "bench.stepFreeShorter.other":
    "{count} son más cortas en metros pero cuestan más: las rutas minimizan el costo de caminar, y una calzada cuenta como tres veces su longitud.",
  "bench.traveller.adultAnkle": "adulto, tobillo",
  "bench.traveller.adultMidCalf": "adulto, mitad de la pantorrilla",
  "bench.traveller.childMidCalf": "niño, mitad de la pantorrilla",
  "bench.traveller.manualWheelchair5": "silla de ruedas manual, 5 cm",
  "bench.outcome.arrived": "llegaron",
  "bench.outcome.atShelter": "en un refugio",
  "bench.outcome.higherLimit": "límite más alto",
  "bench.outcome.shelter": "refugio",
  "bench.outcome.stayInside": "quedarse dentro",
  "bench.outcome.emergencyHelp": "ayuda de emergencia",
  "bench.outcome.notConnected": "sin conexión",
  "bench.outcome.nothing": "nada",
  "bench.fault.F1": "El agua más profunda que el límite es transitable",
  "bench.fault.F2": "El agua de profundidad desconocida cuenta como seca",
  "bench.fault.F3": "Sin el límite máximo de 50 cm para quienes caminan",
  "bench.fault.F4": "Los usuarios de sillas de ruedas pueden usar escalones",
  "bench.fault.F5": "No se ofrece ningún refugio",
  "bench.fault.F6": "No se ofrece un límite más alto",
  "bench.fault.F7": "Sin ayuda de emergencia cuando el agua impide salir de un edificio",
  "bench.fault.F8": "Sin ayuda de emergencia en ningún caso",
  "bench.fault.F9": "La ruta recomendada ignora el agua dentro del límite (α = 0)",
  "bench.fault.F10": "Los usuarios de ayudas para la movilidad pueden usar caminos con más pendiente que 1:14",
};

export default messages;
