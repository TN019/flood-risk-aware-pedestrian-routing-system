import type { Messages } from "./en";

// Korean.
const messages: Messages = {
  // ---------------------------------------------------------------- shared
  "language.label": "언어",
  "app.title": "Southbank 침수 대비 보행 경로",
  "unit.min": "{count}분",
  "depth.unknown": "알 수 없음",
  "depth.none": "없음",
  "depth.withLabel": "{depth} ({label})",
  "route.recommended": "추천 경로",
  "route.safe_shortest": "한도 내 최단 경로",
  "route.shortest": "최단 경로(침수 무시)",
  "route.downgrade": "더 높은 한도로",
  "route.refuge": "대피처로",
  "route.least_water": "물이 가장 적은 경로",
  "error.unreachable": "경로 안내 서비스에 연결할 수 없습니다. 인터넷 연결을 확인하고 다시 시도하세요.",
  "error.status": "경로 안내 서비스에서 오류가 발생했습니다({status}).",

  // ---------------------------------------------------------------- the app: panel
  "app.tagline": "직접 정한 깊이보다 깊은 물은 피해 가는 도보 경로입니다.",
  "app.panel": "경로 계획",
  "app.sheetMore": "지도 더 보기",
  "app.sheetDetails": "자세히 보기",
  "app.loadError": "지도 데이터를 불러올 수 없습니다.",
  "app.planError": "이 이동 경로를 계획할 수 없습니다.",
  "app.planning": "경로 계획 중…",
  "app.safety":
    "경로는 모델로 추정한 상황을 바탕으로 한 안내일 뿐이며, 이 추정은 불완전하거나 틀릴 수 있고 홍수 상황은 빠르게 변합니다. 꼭 필요한 경우가 아니라면 절대 홍수로 불어난 물 속을 걷지 마세요. 긴급 구조 기관의 지시를 따르고, 응급 상황에서는 000에 전화하세요(홍수나 폭풍 피해 도움은 VICSES 132 500).",
  "app.credits": "지도 데이터 © OpenStreetMap 기여자. 침수 시나리오: 각 단계 아래의 '출처'를 참조하세요.",
  // The pill on the map: "Next click sets the start" / "… the destination".
  "app.nextClick": "다음 클릭: {target} 지정",
  "app.nextClick.start": "출발지",
  "app.nextClick.destination": "목적지",

  "trip.label": "출발지와 목적지",
  "trip.start": "출발지",
  "trip.destination": "목적지",
  "trip.locate": "현재 위치 사용",
  "trip.swap": "바꾸기",
  "trip.clear": "지우기",
  "trip.hint": "장소를 검색하거나 지도를 클릭하세요. 첫 번째 클릭은 출발지, 다음 클릭은 목적지가 됩니다.",
  "trip.outside": "Southbank 안(검은색 경계선 안쪽)의 지점을 고르세요.",
  "trip.placeOutside": "{place}의 위치는 Southbank 밖입니다.",
  "trip.noGeolocation": "이 브라우저에서는 위치 정보를 사용할 수 없습니다. 대신 지도를 클릭해 출발지를 지정하세요.",
  "trip.locating": "현재 위치를 찾는 중…",
  "trip.locationOutside": "현재 위치가 Southbank 밖입니다. 대신 지도를 클릭해 가상의 현재 위치를 지정하세요.",
  "trip.locationFailed":
    "위치를 확인할 수 없습니다(권한이 거부되었거나 지원되지 않음). 대신 지도를 클릭해 출발지를 지정하세요.",
  "trip.yourLocation": "내 위치",
  "trip.pointOnMap": "지도상의 지점",
  "trip.pointAt": "{place} ({lat}, {lon})",

  "search.onMap": "지도에서 지정",
  "search.onMapActive": "다음 지도 클릭으로 지정",
  "search.change": "변경",
  "search.placeholder": "예: Eureka Tower, 1 City Road",
  "search.button": "검색",
  "search.tooShort": "세 글자 이상 입력하세요.",
  "search.failed": "검색에 실패했습니다.",
  "search.noMatch": "Southbank 안에서 일치하는 장소가 없습니다. 다른 이름으로 검색하거나 지도를 클릭하세요.",

  // ---------------------------------------------------------------- flood conditions
  "conditions.title": "침수 상황",
  "conditions.group": "침수 시나리오",
  "conditions.none": "없음",
  "conditions.over": "{depth} 초과",
  // {range}: where the water reaches, from the API, e.g. "성인 발목까지"; {depth} is bold.
  "conditions.water":
    "물 높이: {range} (키 {height} cm 성인 기준 {band}). 이곳 침수된 보도의 일반적인 물 깊이: {depth}.",
  "conditions.dry": "고인 물이 없습니다.",
  "conditions.sources": "출처",

  // ---------------------------------------------------------------- the traveller
  "you.title": "나의 정보",
  "you.height": "키",
  "you.aid": "이동 보조기기",
  "you.aidNone": "없음",
  // {aid}: the device, from the API, e.g. "수동 휠체어".
  "you.aidDepth": "{aid} 이용 시 최대 물 깊이",
  "you.aidNote":
    "바퀴 달린 보조기기의 한도는 키가 아니라 기기의 앞바퀴(캐스터) 축, 섀시(차체 하부), 제조사 권고에 따라 정해집니다. 경로는 계단이나 측정된 경사도가 1:14보다 가파른 보도를 절대 이용하지 않습니다.",
  "you.wading": "걸어서 건널 수 있는 최대 물 깊이",
  "you.limit": "나의 한도: {limit}",
  "you.cap": "(어떤 경우에도 최대 {cap})",
  "you.preference": "경로 선호",
  "you.preferenceNote":
    "한도보다 깊은 물은 항상 피합니다. 이 설정은 한도 이내의 물을 돌아서 갈 만한지만 정합니다.",
  "you.advanced": "고급",
  "you.alpha": "위험 가중치 α: {alpha}",
  "you.alphaNote": "한도에 딱 맞는 깊이의 물 한 미터를 피하기 위해 더 걸을 만한 거리(미터 단위).",
  "you.alphaBack": "선호 설정으로 돌아가기",

  // ---------------------------------------------------------------- trip results
  "origin.unknownWater": "깊이를 알 수 없는 물",
  "origin.water": "{depth} 깊이의 물",
  "origin.overLimit": "현재 {water}({label}) 속에 서 있으며, 한도보다 깊습니다.",
  "origin.deep": "현재 {water}({label}) 속에 서 있습니다. 조심해서 움직이세요. 도움을 요청할 수 있습니다.",
  "origin.veryDeep": "이곳의 물은 {depth} 깊이로, 무릎보다 높습니다. 움직이기 전에 도움을 요청하는 것을 권장합니다.",
  "origin.criticalUnknown": "이곳의 물 깊이는 알 수 없습니다.",
  "origin.critical": "이곳의 물은 {depth} 깊이입니다({label}).",
  "origin.criticalAction": "가능하면 지금 있는 곳에 그대로 머무르고 즉시 도움을 요청하세요.",

  "emergency.title": "긴급 도움 — {advice}",
  "emergency.available": "요청 가능",
  "emergency.recommended": "권장",
  "emergency.stronglyRecommended": "강력히 권장",
  "emergency.onlyOption": "유일한 방법",
  "emergency.cutOff": "깊은 물에 고립되어 있습니다. 실내에 머무르고, 건물 안으로 물이 들어오면 더 높은 층으로 이동하세요.",
  "emergency.note":
    "생명이 위험한 사람이 있으면 000. 물에 갇혔거나 건물 안으로 물이 들어오는 등 홍수 관련 도움은 VICSES.",

  "compare.title": "경로 비교",
  "compare.notSafe": "안전하지 않음",
  "compare.deepest": "최대 깊이 {depth} · 물속 구간 {water}",
  "compare.overLimit": "한도 초과 구간 {count}개",
  "compare.hint": "경로를 선택하면 지도에 표시됩니다.",
  "compare.blocked": "이 시나리오에서는 네트워크 구간 {count}개가 한도를 초과합니다.",
  "access.avoidsSteps": "모든 경로가 최단 경로 상의 계단을 피합니다.",
  "access.avoidsSteep": "모든 경로가 최단 경로 상의 1:14보다 가파른 길을 피합니다.",
  "access.avoidsBoth": "모든 경로가 최단 경로 상의 계단과 1:14보다 가파른 길을 피합니다.",
  "access.stepFree": "모든 경로가 계단 없는 경로입니다.",
  "gradient.none": "경사도 데이터 없음",
  "gradient.one": "경사도 {gradient}",
  "gradient.range": "경사도 {from} ~ {to}",
  "trip.fromTo": "{from}에서 {to}까지.",
  "trip.selectedPoint": "선택한 지점",
  "trip.placeAccess": "{place} ({access})",

  // ---------------------------------------------------------------- the next step card
  "next.label": "다음 단계",
  "next.go": "출발해도 됩니다: 이 경로는 한도 이내입니다",
  "next.detour": "추천 경로로 가세요",
  "next.choose": "한도 이내로 갈 수 있는 경로가 없습니다. 하나를 고르세요:",
  "next.downgrade": "한도 이내로 갈 수 있는 경로가 없습니다",
  "next.shelterCritical": "가능하면 지금 있는 곳에 머무르고 도움을 요청하세요",
  "next.shelterFold": "도움을 기다릴 수 없다면: 대피처로 가는 길",
  "next.shelter": "대피처로 가서 기다리세요",
  "next.stay": "물이 빠질 때까지 {place} 안에 머무르세요",
  "next.help": "여기서 안전하게 빠져나갈 길이 없습니다: 도움을 요청하세요",
  "next.helpBody": "갈 수 있는 대피처가 없습니다. 갈 수 있는 가장 높은 곳에 머무르세요.",
  "next.unreachable": "이 지점들을 잇는 경로가 없습니다",
  "next.show": "지도에 표시",
  "next.shown": "지도에 표시됨",
  // {water}: from the API, e.g. "무릎까지 오는 물", "얕은 물웅덩이".
  "next.accept": "허용: {water} ({depth})",
  "next.useLimit": "이 한도 사용",
  "next.refuge": "대피처에서 기다리기: {name}",
  // {entrance}: from the API, e.g. "주 출입구".
  "next.refugeWay": "{entrance}까지: {route}. 물이 빠질 때까지 그곳에서 기다리세요.",
  "next.refugeOverLimit": "가는 길에 한도보다 깊은 물을 지나야 하지만, 물이 가장 얕은 탈출 경로입니다.",
  "next.stayInside": "{place} 안에 머무르세요",
  "next.wait": "물이 빠질 때까지 기다리세요.",
  "next.leastWater": "물이 가장 적은 길",
  "next.routeLine": "{distance} · {time} · 최대 깊이 {depth}",
  "metric.walk": "도보",
  "metric.vsShortest": "최단 경로 대비 +{percent}%",
  "metric.estimated": "예상",
  "metric.unknown": "알 수 없음",
  "metric.dry": "물 없음",
  "metric.deepest": "최대 물 깊이",
  "metric.inWater": "물속 구간",
  "metric.steepest": "최대 경사",
  "metric.gentlest": "최소 경사",
  "metric.noGradient": "경사도 데이터 없음",

  // Why no route fits: {depth} and {limit} are depths such as "32 cm", {label} where the water
  // reaches (from the API), {aid} the traveller's device and {place} the destination's name.
  "why.unknown": "어느 길로 가든 깊이를 알 수 없는 물을 지나야 합니다.",
  "why.unknownTo": "{place}까지 어느 길로 가든 깊이를 알 수 없는 물을 지나야 합니다.",
  "why.overLimit":
    "어느 길로 가든 최소 {depth} 깊이의 물({label})을 지나야 하며, 이는 나의 한도 {limit}보다 깊습니다. 가장 깊은 지점은 지도에 표시되어 있습니다.",
  "why.overLimitTo":
    "{place}까지 어느 길로 가든 최소 {depth} 깊이의 물({label})을 지나야 하며, 이는 나의 한도 {limit}보다 깊습니다. 가장 깊은 지점은 지도에 표시되어 있습니다.",
  "why.overCap":
    "어느 길로 가든 최소 {depth} 깊이의 물({label})을 지나야 하며, 이는 누구에게든 경로를 안내하는 최대 깊이인 {limit}보다 깊습니다. 가장 깊은 지점은 지도에 표시되어 있습니다.",
  "why.overCapTo":
    "{place}까지 어느 길로 가든 최소 {depth} 깊이의 물({label})을 지나야 하며, 이는 누구에게든 경로를 안내하는 최대 깊이인 {limit}보다 깊습니다. 가장 깊은 지점은 지도에 표시되어 있습니다.",
  "why.overAidCap":
    "어느 길로 가든 최소 {depth} 깊이의 물({label})을 지나야 하며, 이는 {aid} 이용자에게 경로를 안내하는 최대 깊이인 {limit}보다 깊습니다. 가장 깊은 지점은 지도에 표시되어 있습니다.",
  "why.overAidCapTo":
    "{place}까지 어느 길로 가든 최소 {depth} 깊이의 물({label})을 지나야 하며, 이는 {aid} 이용자에게 경로를 안내하는 최대 깊이인 {limit}보다 깊습니다. 가장 깊은 지점은 지도에 표시되어 있습니다.",
  // What the recommended route gains over the shortest way: {distance}, {extra} and {water} are
  // distances such as "120 m".
  "detour.unknown":
    "최단 경로({distance})는 깊이를 알 수 없는 물을 지납니다. 이 경로는 그 물을 피하기 위해 {extra} 더 걷습니다.",
  "detour.overLimit":
    "최단 경로({distance})는 한도보다 깊은, 최대 {depth}({label})의 물을 지납니다. 이 경로는 한도 이내로 가기 위해 {extra} 더 걷습니다.",
  "detour.avoid":
    "이 경로는 최대 {depth}({label}) 깊이의 물 {water} 구간을 피하기 위해 최단 경로보다 {extra} 더 걷습니다.",

  // ---------------------------------------------------------------- map and legend
  "map.label": "Southbank 지도",
  "map.unknownDepth": "깊이 알 수 없음 · 너무 깊은 것으로 간주",
  "map.overLimit": "한도 초과",
  "map.shelter": "대피처: {name}",
  "map.deepest": "물이 가장 적은 경로의 가장 깊은 지점: {depth}",
  "map.deepestUnknown": "물이 가장 적은 경로의 가장 깊은 지점: 깊이 알 수 없음",
  "map.failed": "지도 표시가 멈췄습니다.",
  "map.failedWhy": "브라우저의 그래픽 리소스가 부족합니다.",
  "map.reload": "지도 다시 불러오기",
  "map.failedNote": "이 문제가 계속되면 브라우저를 완전히 종료한 뒤 다시 여세요.",
  "map.zoomIn": "확대",
  "map.zoomOut": "축소",
  "map.attribution": "저작권 표시 열기/닫기",
  "legend.title": "범례",
  "legend.waterOk": "한도 이내의 물",
  "legend.waterOver": "한도 초과 또는 깊이 알 수 없음",
  "legend.shortestUnsafe": "최단 경로(침수 무시, 안전하지 않음)",
  // {label}: a body part from the API, e.g. "무릎".
  "legend.downgradeBody": "{label} 한도로",
  "legend.downgradeAid": "더 높은 한도로({depth})",
  "legend.deepest": "물이 가장 적은 경로의 가장 깊은 지점",

  // ---------------------------------------------------------------- getting help
  "help.button": "도움 요청",
  "help.close": "닫기",
  "help.call000": "000에 전화",
  "help.lifeDanger": "누군가의 생명이 위험한 경우.",
  "help.ses": "홍수나 폭풍 피해 도움: 물에 갇힘, 실내로 물이 들어옴, 나무가 쓰러짐.",
  "help.simulated": "전화 버튼을 누르면 휴대폰의 전화 앱이 열립니다. 이 버전에서 SOS 알림은 모의 기능입니다.",
  "sos.button": "주변 사람에게 알리기(SOS)",
  "sos.sent": "{seconds}초 전에 SOS를 보냈습니다. 공유 내용: {shared} (모의).",
  "sos.undo": "취소({seconds}초)",
  // What an SOS shares, put into "공유 내용: {shared}".
  "sos.noLocation": "위치 없음(공유하려면 출발지를 지정하세요)",
  "sos.currentLocation": "현재 위치",
  "sos.startAsLocation": "내 위치로 지정한 출발지",
  "sos.here": "내 위치",
  "sos.hereWithDepth": "내 위치와 물 깊이 {depth}",

  // ---------------------------------------------------------------- shared by /reference and /benchmark
  "doc.back": "← Southbank 침수 대비 보행 경로",
  "doc.sections": "목차",
  "basis.cited": "인용",
  "basis.derived": "도출",
  "basis.chosen": "판단",
  "basis.chosenTitle": "판단에 따른 값",

  // ---------------------------------------------------------------- /reference
  "ref.title": "출처 및 참고 자료",
  "ref.pageTitle": "출처 및 참고 자료 · Southbank 침수 대비 보행 경로",
  "ref.intro":
    "지도, 보행 네트워크, 침수 시나리오의 출처와 각 깊이 한도의 근거를 설명합니다. 표의 값은 실행 중인 시스템에서 읽어 온 것이므로, 경로 계산에 실제로 쓰이는 값입니다.",
  "ref.nav.data": "데이터",
  "ref.nav.scenarios": "침수 시나리오",
  "ref.nav.limits": "깊이 한도",
  "ref.nav.documents": "문헌",
  "ref.nav.licences": "라이선스",
  "ref.nav.notCovered": "다루지 않는 부분",
  "ref.data.title": "데이터",
  "ref.data.data": "데이터",
  "ref.data.use": "용도",
  "ref.data.licence": "라이선스",
  "ref.scenarios.title": "침수 시나리오",
  "ref.scenarios.intro":
    "각 시나리오는 공개된 수위를 지형 모델에 적용한 것입니다. 강물과 폭풍 해일, 만조 때 역류하는 배수구, 낮은 곳에 고이는 빗물을 반영합니다. 침수 단계는 침수된 보도의 일반적인 물 깊이로 정합니다.",
  "ref.scenarios.typical": "일반적인 깊이 {depth}",
  "ref.limits.title": "깊이 한도",
  "ref.limits.cited": "명시된 출처에서 가져온 값.",
  "ref.limits.derived": "인용한 값에서 계산한 값.",
  "ref.limits.chosen": "값을 정한 출처가 없어 판단으로 정한 값으로, 더 나은 근거가 나오면 가장 먼저 다시 검토할 값입니다.",
  "ref.loading": "현재 값을 불러오는 중…",
  "ref.loadError": "현재 값을 불러올 수 없습니다: {error}",
  "ref.walking": "도보",
  "ref.walkingIntro":
    "이용자는 걸어서 건널 수 있는 최대 물 깊이를 신체 부위로 고르며, 이는 키에 따라 깊이로 환산됩니다. 아래 깊이는 키 {height} cm 성인 기준입니다.",
  "ref.choice": "선택",
  "ref.depth": "깊이",
  "ref.basis": "근거",
  "ref.fraction": "({fraction} × 키)",
  "ref.upperLimit": "모든 사람에게 적용되는 상한",
  "ref.atMost": "최대 {depth}",
  "ref.aids": "휠체어와 전동 스쿠터",
  "ref.aidsIntro":
    "바퀴 달린 이동 보조기기 이용자는 신체 부위 대신 기기에 맞는 수준을 고르며, 계단이나 1:14보다 가파른 길로는 절대 안내되지 않습니다. 1:14는 AS 1428.1이 허용하는 가장 가파른 경사로 기울기입니다. 모든 경로에는 측정된 최대·최소 경사도가 표시됩니다.",
  "ref.deviceLevel": "기기 및 수준",
  "ref.cap": "(상한)",
  "ref.levels": "침수 단계",
  "ref.levelsIntro":
    "네 단계의 이름은 키 {height} cm 성인에게 일반적인 물이 닿는 높이에 따라 붙였습니다. 침수 심각도를 구분하는 데 쓰이는 발목, 무릎, 엉덩이 수위선(Feng, Brenner & Sester, 2020)을 사용하며, 신체 부위 높이는 Drillis & Contini (1966)를 따릅니다.",
  "ref.level": "단계",
  "ref.typicalWater": "일반적인 물 높이",
  "ref.over": "{depth} 초과",
  "ref.seeParameters": "docs/parameters.md 참조",
  "ref.documents.title": "문헌",
  "ref.documents.flooding": "Southbank의 침수",
  "ref.documents.people": "홍수 물 속의 사람과 접근성",
  "ref.documents.mobility": "휠체어와 전동 스쿠터",
  "ref.documents.note": "인용 문헌은 원어로 표기합니다.",

  "ref.licences.title": "라이선스",
  "ref.licences.software": "이 소프트웨어는 {licence}에 따라 배포됩니다.",
  "ref.licences.osm":
    "처리된 보행 네트워크처럼 OpenStreetMap에서 파생된 데이터는 {licence}에 따라 이용할 수 있으며, 출처를 © OpenStreetMap 기여자로 표시합니다.",
  "ref.licences.others": "다른 데이터 세트는 위에 적힌 라이선스를 따릅니다. 문헌은 인용만 하며 재배포하지 않습니다.",
  "ref.notCovered.title": "다루지 않는 부분",
  "ref.notCovered.notice":
    "이 서비스는 공식 홍수 경보 서비스가 아닙니다. VICSES와 Bureau of Meteorology의 경보를 따르고, 응급 상황에서는 000에 전화하며, 홍수나 폭풍 피해 도움은 VICSES 132 500에 전화하세요.",
  "ref.footer": "모든 매개변수와 그 설정 위치 및 이유: {parameters}. 시스템 작동 방식: {architecture}.",

  // What each dataset is used for (its name, publisher and licence stay as published).
  "ref.data.osm.name": "보행 네트워크, 건물, 출입구",
  "ref.data.osm.use": "경로가 따라가는 길, 계단, 출발지·목적지·대피처로 쓰이는 건물과 그 출입구.",
  "ref.data.clue.use": "시스템이 다루는 범위인 Southbank 경계.",
  "ref.data.pits.use": "지표면으로 열려 있는 배수구 유입구. 만조 때 배수관을 통해 물이 역류해 나오는 곳입니다.",
  "ref.data.steepness.use":
    "시가 관리하는 보도 구간별 경사도. 모든 경로에 측정된 최대·최소 경사도를 표시하며, 휠체어와 스쿠터 경로는 1:14보다 가파른 길을 제외합니다.",
  "ref.data.pedestrian.use": "OpenStreetMap 보행 네트워크를 검증하는 데 쓰는 별도의 보행 네트워크.",
  "ref.data.dem.use": "지반 높이. 이를 바탕으로 각 지점의 물 깊이를 계산합니다.",
  "ref.data.overlays.use":
    "100년에 1번 꼴로 일어나는 홍수 때 침수가 예상되는 지역. Streamlit 앱에서 참고용으로 보여 주며, 경로 계산에는 쓰지 않습니다.",
  "ref.data.search.name": "장소 검색",
  "ref.data.search.use": "검색창에 입력한 장소 찾기.",
  "ref.data.basemap.name": "배경 지도",
  "ref.data.basemap.use": "경로 아래에 그려지는 지도. 불러오지 못하면 OpenStreetMap 자체 타일을 사용합니다.",
  "ref.data.census.use":
    "이 사이트에서 제공하는 언어: Southbank(SAL22315) 및 Southbank (West) – South Wharf(SA2 206041508) 지역의 가정에서 가장 많이 쓰는 언어.",

  // What each document is used for (the citation stays as published).
  "ref.doc.melbourneWater.use":
    "Southbank의 침수 양상(폭풍 해일과 강물 흐름, 지역 빗물, 만조 때 물을 배출하지 못하는 배수구). 500 mm까지를 안전한 보행 접근으로, 취약 계층 용도에는 300 mm를 기준으로 봅니다.",
  "ref.doc.ghd.use":
    "Port Phillip Bay의 폭풍 해일 수위(Table 1): 20년에 1번 꼴 1.25 m, 100년에 1번 꼴 1.60 m, 2100년의 100년에 1번 꼴 2.40 m AHD.",
  "ref.doc.waterTechnology.use": "Williamstown의 최고 천문조위 0.59 m AHD(Table 2-1): 경미 침수 단계.",
  "ref.doc.floodSubPlan.use": "만조는 배수구의 배수 능력을 떨어뜨리고, 역류한 물이 배수구 주변으로 넘쳐 나옵니다.",
  "ref.doc.floodGuide.use":
    "Southbank 수위계 기준으로 침수가 예상되는 거리(시나리오 검증에 사용), 그리고 이 수위계의 주요 홍수 수위.",
  "ref.doc.vpp.use": "2100년까지 해수면 0.8 m 상승을 고려한 계획: 극심 침수 단계.",
  "ref.doc.drillis.use": "키에 대한 비율로 나타낸 발목, 무릎, 엉덩이 높이.",
  "ref.doc.feng.use": "홍수 심각도를 구분하는 수위선으로서의 발목, 무릎, 엉덩이: 네 침수 단계의 경계.",
  "ref.doc.smith.use":
    "사람에 대한 깊이 한도(H2) 0.5 m 및 어린이가 물을 건널 수 있는 한도. 취약한 사람은 흐르는 홍수 물을 피해야 합니다.",
  "ref.doc.abs.use": "성인 평균 키 1.69 m: 침수 단계 설명에 쓰는 기준 성인 키 1.70 m의 근거.",
  "ref.doc.as1428.use":
    "접근 가능한 이동 경로에는 계단도, 1:14보다 가파른 경사로도 없습니다(연석 경사로는 1.52 m 길이에 최대 1:8). 따라서 휠체어와 스쿠터 경로는 둘 다 이용하지 않습니다.",
  "ref.doc.minniemobil.use": "2.5 cm보다 깊은 물은 건너지 말 것: 전동 스쿠터의 한도.",
  "ref.doc.pride.use": "여행용 스쿠터 모터 부분의 지상고 3.5 cm.",
  "ref.doc.prideManuals.use": "고인 물을 피할 것. 5 cm보다 높은 연석은 오르지 말 것.",
  "ref.doc.nitrum.use":
    "앞바퀴(캐스터) 크기 3~6인치. 캐스터 축은 지름의 절반 높이에 있습니다(4인치는 5.1 cm, 6인치는 7.6 cm).",
  "ref.doc.q500.use": "전동 휠체어의 지상고 3인치(7.6 cm).",
  "ref.doc.permobil.use": "전동 휠체어의 지상고 약 75 mm.",
  "ref.doc.invacare.use":
    "전기 장치는 IPX4(EN 60529) 시험 기준: 물이 튀는 것에 대한 보호이며 물에 잠기는 것은 견디지 못합니다. ISO 7176-2 기준 동적 안정성 6°(10.5%): 1:14보다 크지만, 전동 휠체어에도 여전히 1:14를 적용합니다(판단).",

  // The basis of each limit.
  "ref.basis.no_wading": "비가 오면 어느 포장도로에나 생기는 얇은 물막. 이보다 깊은 물은 물을 건너는 것으로 봅니다.",
  "ref.basis.ankle": "0.039 × 키 (Drillis & Contini, 1966).",
  "ref.basis.lower_calf": "발목에서 무릎 쪽으로 삼분의 일 되는 지점.",
  "ref.basis.mid_calf": "발목과 무릎의 중간.",
  "ref.basis.knee": "0.285 × 키 (Drillis & Contini, 1966). 최대 50 cm.",
  "ref.basis.manualNoWater": "보행자와 같은 마른 포장도로 허용치. 제조사는 고인 물을 피하라고 권고합니다.",
  "ref.basis.castorAxle": "4인치 앞바퀴(캐스터)의 축 높이(5.1 cm). Pride 설명서의 연석 한도 5 cm이기도 합니다.",
  "ref.basis.largeCastorAxle":
    "6인치 앞바퀴(캐스터)의 축 높이(7.6 cm). 수동 휠체어로 물을 건널 수 있는 깊이를 정한 출처는 없습니다.",
  "ref.basis.sameAsWalkers": "보행자와 같은 마른 포장도로 허용치.",
  "ref.basis.belowChassis":
    "약 7.5 cm인 지상고보다 2.5 cm 낮은 값. 전기 장치는 물 튀김에만 견디는 등급이며, 이 여유는 판단으로 정했습니다.",
  "ref.basis.shallowPuddle":
    "제조사가 명시한 유일한 깊이(MinnieMobil). 여행용 스쿠터의 모터 지상고 3.5 cm보다 낮습니다.",
  "ref.basis.hardLimit":
    "Melbourne Water의 Southbank 계획은 500 mm까지를 안전한 보행 접근으로 보며, 0.5 m는 사람에 대한 H2 깊이 한도입니다(Smith, Davey & Cox, 2014). 허벅지와 허리는 선택지에 없습니다. 거의 모든 사람에게 50 cm로 제한되기 때문입니다.",
  "ref.basis.aidCap":
    "사람이 탄 휠체어나 스쿠터가 홍수 물 속에서 얼마나 안정적인지 측정한 연구가 없으므로, 각 수준은 기기와 제조사 정보를 따르며 보행자의 50 cm보다 훨씬 낮습니다.",

  // What the system does not cover.
  "ref.limit.static":
    "침수 시나리오는 지반 높이와 공개된 수위로 만든 정적 추정치이며 수리 모델이 아닙니다. 물의 흐름, 유속, 시간 변화, 배수 능력은 반영하지 않습니다.",
  "ref.limit.surcharge":
    "평상시 조위에서 비로 인해 배수구에서 물이 역류하는 경우는 반영하지 못합니다. 배수구와 배수관의 높이가 공개되지 않았기 때문입니다. 짧은 폭풍우만으로도 경미 침수 시나리오보다 깊은 물이 생길 수 있습니다.",
  "ref.limit.river":
    "강 수위는 만(bay)의 조위를 그대로 사용합니다. 강물 흐름으로 수위가 더 높아질 수 있으므로, 강의 물 깊이는 최솟값입니다.",
  "ref.limit.shelters":
    "출입구가 있는 모든 건물을 대피처로 봅니다. 일반에 개방되어 있는지는 데이터로 알 수 없습니다.",
  "ref.limit.gradients":
    "경사도는 City of Melbourne이 측량한 보도에서만 알 수 있습니다(Southbank 보도 길이의 약 삼분의 이). 차도나 사유 통로처럼 측량값이 없는 길은 가파른 것으로 보지 않으며, 경로의 최대·최소 경사도는 측정된 부분만 반영합니다.",
  "ref.limit.sections":
    "보도 구간의 경사도는 가장 낮은 지점과 가장 높은 지점 사이의 평균이므로, 긴 구간 안의 짧고 가파른 부분은 놓칠 수 있습니다. 서로 다른 높이를 잇는 것처럼 보이는 구간(다리와 고가 통로)은 제외합니다.",

  // ---------------------------------------------------------------- /benchmark
  "bench.title": "벤치마크",
  "bench.pageTitle": "벤치마크 · Southbank 침수 대비 보행 경로",
  "bench.intro":
    "경로가 주어진 데이터에서 규칙을 지키는지 가상의 데이터(작은 테스트 마을)와 실제 Southbank 네트워크에서 자동으로 확인합니다. 예측은 첫 실행 전에 {benchmarks}에 작성했습니다.",
  "bench.run": "{date} 실행, 커밋 {commit}. 교차점 {nodes}개와 구간 {edges}개로 이루어진 네트워크.",
  "bench.unknownCommit": "알 수 없음",
  "bench.loadError": "벤치마크 결과를 불러올 수 없습니다: {error}",
  "bench.loading": "결과를 불러오는 중…",
  "bench.footer": "{folder}에서 {command} 명령으로 다시 실행하세요. 결과는 {file}에 저장됩니다.",
  "bench.measured": "측정값",
  "bench.asPredicted": "예측대로",
  "bench.notAsPredicted": "예측과 다름",
  "bench.share": "{total} 중 {count}",
  "bench.none": "없음",
  "bench.yes": "예",
  "bench.no": "아니요",
  "bench.algorithm": "알고리즘 계층",
  "bench.correctness": "정확성",
  "bench.pathFinder": "NetworkX와 비교한 경로 탐색",
  "bench.pathFinderText":
    "노드 간: 무작위 쌍 {pairs}개에서 비용이 같음(그중 {same}개는 경로도 동일). 라우터를 거친 경우(스냅과 접근 구간 포함): 무작위 이동 {routes}건에서 길이가 같음.",
  "bench.minimax": "전수 탐색과 비교한 가장 안전한 경로 탐색",
  "bench.minimaxText":
    "가능한 가장 낮은 최대 깊이와 그 깊이에서의 최단 경로가, 무작위 그래프 {graphs}개의 노드 쌍 {pairs}개에 대해 모든 경로를 나열한 결과와 일치했습니다.",
  "bench.predictions": "직접 도출한 예측",
  "bench.predictionsText": "테스트 마을 사례 A–J: {town} 충족. Southbank 속성 R-A~R-I: {southbank} 충족.",
  "bench.faults": "결함 주입",
  "bench.faultsText":
    "각 결함은 일부러 안전 규칙 하나를 깨뜨리며, 그다음 전체 테스트 모음을 결함이 있는 코드에 대해 실행합니다. 결함이 없는 원래 코드에서는 테스트 {tests}개 중 {failed}개가 실패합니다.",
  "bench.fault": "결함",
  "bench.testsFailed": "실패한 테스트",
  "bench.casesFailed": "실패한 테스트 마을 사례",
  "bench.caught": "검출",
  "bench.safety": "보행자 안전",
  "bench.cost": "안전과 그 비용",
  "bench.costText":
    "각 침수 단계마다 무작위 이동 {trips}건. 계획 {plans}건 중 추천 경로가 이용자의 한도를 넘는 물을 지난 경우는 없었습니다{overLimit}. 단순 최단 경로가 한도를 넘는 물을 지나는 경우, 추천 경로는 표에 나온 중앙값만큼 더 길고, 한도를 넘는 물 구간을 중앙값 길이만큼 피합니다.",
  "bench.costOverLimit": " (실제로는 {count}건 있었음)",
  "bench.levelTraveller": "단계와 이용자",
  "bench.withRoute": "한도 이내 경로",
  "bench.shortestUnsafe": "최단 경로가 안전하지 않음",
  "bench.longerBy": "늘어난 길이",
  "bench.avoided": "피한 한도 초과 물 구간",
  "bench.offered": "경로가 없을 때 제공한 것",
  "bench.rising": "불어나는 홍수: 이동 중 경로 재설정",
  "bench.risingText":
    "홍수가 불어나는 동안 걷는 이용자({traveller})의 이동 {trips}건: {schedule}. 물이 불어날 때마다 현재 위치에서 경로를 다시 계획합니다.",
  "bench.risingFrom": "{minutes}분부터 {level}",
  "bench.risingViolations": "한도 이내라고 안내한 경로에서 한도를 넘는 물을 걸은 거리: {metres}.",
  "bench.risingReroutes":
    "이동 {trips}건에서 경로를 {reroutes}번 재설정했습니다. 그중 {caught}번은 이용자가 서 있는 곳의 물이 이미 한도를 넘게 불어나 있었고, 가장 안전한 탈출 경로는 그런 물을 모두 합쳐 {metres} 지났습니다.",
  "bench.risingOutcomes": "결과: {outcomes}.",
  "bench.risingExtra": "도착한 이용자는 처음 계획보다 {median} 더 걸었습니다(중앙값, 90번째 백분위수 {p90}).",
  "bench.finding": "발견 사항:",
  "bench.findingText":
    "경로가 Southbank 밖의 네트워크 여유 구역을 지나는 동안 홍수가 불어난 경우가 {count}번 있었습니다. 이 구역에서는 이동을 계획할 수 없습니다(출발지는 Southbank 안에 있어야 함). 이용자는 기존 경로를 그대로 따라가 그곳에서 한도를 넘는 물을 모두 합쳐 {metres} 걸었습니다. 경로가 지날 수 있는 네트워크의 어느 곳에서든 경로를 다시 계획할 수 있어야 합니다.",
  "bench.access": "공공 구역 접근성",
  "bench.stepFree": "건물 간 계단 없는 연결성",
  "bench.stepFreeText":
    "평상시 조건에서 도보로 연결된 무작위 건물 쌍 {pairs}개. 계단 없는 경로는 1:14보다 가파른 길도 제외하는데, 도보 경로 중 {steep}개가 이런 길을 이용합니다. 계단 없는 경로는 {routes}개 쌍에 존재하며, 그중 {same}개는 도보 경로와 같습니다(가는 길에 계단이나 가파른 길이 없음). 전체 쌍에서 계단 없는 경로는 중앙값 {median}, 90번째 백분위수 {p90}, 최대 {max}만큼 더 깁니다. 계단을 이용하거나({steps}) 1:14보다 가파른 길을 이용하거나({steepUsed}) 도보 경로보다 비용이 적은({cheaper}) 계단 없는 경로는 없습니다.",
  "bench.stepFreeShorter.one":
    "{count}개는 미터 단위로는 더 짧지만 비용은 더 큽니다. 경로는 도보 비용을 최소화하며, 차도는 길이의 세 배로 계산합니다.",
  "bench.stepFreeShorter.other":
    "{count}개는 미터 단위로는 더 짧지만 비용은 더 큽니다. 경로는 도보 비용을 최소화하며, 차도는 길이의 세 배로 계산합니다.",
  // The benchmark's travellers, outcomes and faults (docs/benchmark.json writes them in English).
  "bench.traveller.adultAnkle": "성인, 발목",
  "bench.traveller.adultMidCalf": "성인, 종아리 중간",
  "bench.traveller.childMidCalf": "어린이, 종아리 중간",
  "bench.traveller.manualWheelchair5": "수동 휠체어, 5 cm",
  "bench.outcome.arrived": "도착",
  "bench.outcome.atShelter": "대피처 도착",
  "bench.outcome.higherLimit": "더 높은 한도",
  "bench.outcome.shelter": "대피처",
  "bench.outcome.stayInside": "실내 대기",
  "bench.outcome.emergencyHelp": "긴급 도움",
  "bench.outcome.notConnected": "연결 안 됨",
  "bench.outcome.nothing": "없음",
  "bench.fault.F1": "한도보다 깊은 물을 지나갈 수 있음",
  "bench.fault.F2": "깊이를 알 수 없는 물을 마른 길로 간주",
  "bench.fault.F3": "보행자에게 50 cm 절대 한도 없음",
  "bench.fault.F4": "휠체어 이용자가 계단을 이용할 수 있음",
  "bench.fault.F5": "대피처를 제안하지 않음",
  "bench.fault.F6": "한도 상향을 제안하지 않음",
  "bench.fault.F7": "건물 안에 고립되었을 때 긴급 도움 없음",
  "bench.fault.F8": "긴급 도움이 전혀 없음",
  "bench.fault.F9": "추천 경로가 한도 이내의 물을 무시함(α = 0)",
  "bench.fault.F10": "이동 보조기기 이용자가 1:14보다 가파른 길을 이용할 수 있음",
};

export default messages;
