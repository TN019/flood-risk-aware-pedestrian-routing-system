# Languages

The web client (the app, `/reference` and `/benchmark`) is offered in English, Spanish, Chinese
(Simplified), Hindi and Korean. The `/slides` page, the Streamlit app and the documentation are in
English only. How the text gets to the page is described in
[architecture.md](architecture.md#languages); why these languages, with the census figures, is in
[parameters.md](parameters.md#languages).

## Where the text is

| Text | Where | English source |
|---|---|---|
| The pages' own text | `frontend/src/i18n/messages/<language>.ts` | `en.ts` |
| Text the API composes: limits, depth descriptions, route preferences and their example, route names, errors | `backend/src/floodroute/api/locales/<language>.json` | `en.json` |
| Flood scenario titles and descriptions | the same files, as `scenario.<id>.title` and `scenario.<id>.description` | `data/scenarios/*.json` |
| Flood scenario source notes | the same files, as `scenario.source.<the English note>` (most notes are shared by several scenarios, so each is translated once) | `data/scenarios/*.json` (`sources`) |

Each language has every key of the English file, with the same `{placeholders}` and the same
numbers; tests check this (`frontend/src/i18n/i18n.test.ts`, `backend/tests/test_i18n.py`). The
one exception to "the same numbers" is the 1 of "1-in-100-year", which a language may leave out
("100-year"). Keys ending in `.one` and `.other` are the two forms of one sentence, picked by a
count with the language's plural rules.

To add a language: add it to `LANGUAGES` in `frontend/src/i18n/languages.ts` (with its name in its
own script) and in `backend/src/floodroute/api/i18n.py`, add the two catalogue files, add its
loader in `frontend/src/i18n/I18n.tsx`, and, for a script the fonts do not cover, a font stack in
`frontend/src/theme.css`.

## Conventions

- **Kept as they are, in every language:** numbers (Western digits, a full stop as the decimal
  point and a comma between thousands: 2.5 cm, 22,631), the unit symbols cm, m, km and %, the
  phone numbers 000 and 132 500, and place and organisation names (Southbank, Melbourne, Crown
  Melbourne, VICSES, Melbourne Water, OpenStreetMap). Names of datasets and documents, their
  authors, years, table numbers and licences, and the full citations on `/reference`, stay in their
  original language (English); in a scenario's source notes only the words around them are
  translated. A word for minutes or seconds may be translated.
- **The same number in the same place.** Writing every number as in English keeps a depth on a
  sign, a gauge and the screen alike, and lets the tests check that no number was changed. Spanish
  readers may expect a decimal comma; the decimal point is used, as in Australia and in Mexican and
  Central American Spanish.
- **Register:** polite and plain. Spanish uses *usted* and neutral Latin American Spanish; Chinese
  uses 您; Hindi uses आप, with common English loanwords where Hindi speakers use them (व्हीलचेयर,
  स्कूटर); Korean uses 합니다 for statements and 하세요 for instructions.
- **Sentences are translated whole.** Placeholders hold values (a depth, a place, a label the API
  sends); the sentence around them is the translator's to shape. Korean sentences avoid particles
  that change with the word before them (은/는, 이/가, 을/를, 와/과, 으로/로) straight after a
  placeholder.
- **Safety text stays as strong as the English.** "Never", "call 000", "stay where you are" are not
  softened.

## Glossary

Key terms, used the same way everywhere.

| English | Español | 中文（简体） | हिन्दी | 한국어 |
|---|---|---|---|---|
| limit (the deepest water a traveller accepts) | límite | 限度 | सीमा | 한도 |
| over / within your limit | por encima de / dentro de su límite | 超过 / 在您的限度以内 | आपकी सीमा से अधिक / के भीतर | 한도 초과 / 한도 이내 |
| upper limit, cap (of a device) | límite máximo | 上限 | अधिकतम सीमा | 상한 |
| flood level | nivel de inundación | 洪水等级 | बाढ़ का स्तर | 침수 단계 |
| Light, Moderate, Heavy, Extreme (flood levels) | Leve, Moderada, Grave, Extrema | 轻度、中度、重度、极端 | हल्की, मध्यम, भारी, अत्यधिक | 경미, 보통, 심각, 극심 |
| flood scenario | escenario de inundación | 洪水情景 | बाढ़ परिदृश्य | 침수 시나리오 |
| water (on a flooded footpath) | agua | 积水 | पानी | 물 |
| water of unknown depth | agua de profundidad desconocida | 深度未知的积水 | अज्ञात गहराई का पानी | 깊이를 알 수 없는 물 |
| ankle | tobillo | 脚踝 | टखना | 발목 |
| lower calf | parte baja de la pantorrilla | 小腿下部 | पिंडली का निचला भाग | 종아리 아래쪽 |
| mid calf | mitad de la pantorrilla | 小腿中部 | पिंडली का बीच का भाग | 종아리 중간 |
| knee | rodilla | 膝盖 | घुटना | 무릎 |
| mid thigh | mitad del muslo | 大腿中部 | जाँघ का बीच का भाग | 허벅지 중간 |
| hip | cadera | 髋部 | कूल्हा | 엉덩이 |
| waist | cintura | 腰部 | कमर | 허리 |
| chest | pecho | 胸部 | छाती | 가슴 |
| shoulders | hombros | 肩部 | कंधे | 어깨 |
| up to the ankle (where water reaches) | hasta el tobillo | 到脚踝 | टखने तक | 발목까지 |
| no wading | no caminar por el agua | 不涉水 | पानी में न चलें | 물을 건너지 않음 |
| shelter (a building to wait in) | refugio | 避难处 | आश्रय | 대피처 |
| steps (a flight of stairs) | escalones | 台阶 | सीढ़ियाँ | 계단 |
| step-free | sin escalones | 无台阶 | बिना सीढ़ियों वाला | 계단 없는 |
| gradient | pendiente | 坡度 | ढलान | 경사도 |
| steeper than 1:14 | con más pendiente que 1:14 | 比 1:14 更陡 | 1:14 से अधिक ढलान वाला | 1:14보다 가파른 |
| route | ruta | 路线 | मार्ग | 경로 |
| Recommended (route) | Recomendada | 推荐路线 | अनुशंसित मार्ग | 추천 경로 |
| Shortest within your limit | La más corta dentro de su límite | 限度内最短路线 | आपकी सीमा के भीतर सबसे छोटा मार्ग | 한도 내 최단 경로 |
| Shortest, ignoring flooding | La más corta, sin tener en cuenta la inundación | 最短路线（不考虑积水） | सबसे छोटा मार्ग, बाढ़ को अनदेखा करके | 최단 경로(침수 무시) |
| With a higher limit | Con un límite más alto | 提高限度后 | ऊँची सीमा के साथ | 더 높은 한도로 |
| Least water (route) | Menos agua | 积水最少 | सबसे कम पानी | 물이 가장 적은 경로 |
| route preference: Shortest, Balanced, Avoid water, Stay as dry as possible | Más corta, Equilibrada, Evitar el agua, Lo más seco posible | 最短、均衡、避开积水、尽量保持干燥 | सबसे छोटा, संतुलित, पानी से बचें, जितना हो सके सूखे रहें | 최단, 균형, 물 피하기, 최대한 젖지 않게 |
| mobility aid | ayuda para la movilidad | 助行设备 | चलने में सहायक उपकरण | 이동 보조기기 |
| manual wheelchair | silla de ruedas manual | 手动轮椅 | मैनुअल व्हीलचेयर | 수동 휠체어 |
| powered wheelchair | silla de ruedas eléctrica | 电动轮椅 | पावर्ड व्हीलचेयर | 전동 휠체어 |
| mobility scooter | scooter de movilidad | 电动代步车 | मोबिलिटी स्कूटर | 전동 스쿠터 |
| castor (front wheel of a wheelchair) and its axle | rueda giratoria delantera, su eje | 前脚轮及其轮轴 | कैस्टर पहिया और उसकी धुरी | 앞바퀴(캐스터)와 그 축 |
| chassis | chasis | 底盘 | चेसिस | 섀시(차체 하부) |
| Get help | Pedir ayuda | 求助 | मदद लें | 도움 요청 |
| emergency help | ayuda de emergencia | 紧急求助 | आपातकालीन मदद | 긴급 도움 |
| Next step | Siguiente paso | 下一步 | अगला कदम | 다음 단계 |
| SOS, VICSES, 000 | SOS, VICSES, 000 | SOS、VICSES、000 | SOS, VICSES, 000 | SOS, VICSES, 000 |
| start, destination | inicio, destino | 起点、目的地 | शुरुआत, मंज़िल | 출발지, 목적지 |
| boundary (of Southbank on the map) | contorno | 边界 | सीमा-रेखा | 경계선 |
| footpath | acera | 人行道 | फ़ुटपाथ | 보도 |
| section (of the walking network) | tramo | 路段 | हिस्सा | 구간 |
| level (of a mobility aid) | nivel | 等级 | स्तर | 수준 |
| Judgement (a value no source sets) | Criterio | 判断 | आकलन | 판단 |
