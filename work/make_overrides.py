# -*- coding: utf-8 -*-
"""project-specific overrides for 35-40.pdf  ->  work/overrides/pN.json"""
import json, os
os.makedirs("overrides", exist_ok=True)
GRAY = "#3A3C3C"; BODY = "#454747"; LINE = "#C8CCCD"; BLUE = "#389FD9"

def T(text, bbox, **kw):
    e = dict(type="text", text=text, bbox=bbox, color=kw.pop("color", BODY)); e.update(kw); return e
def L(bbox, color=LINE, **kw):
    e = dict(type="line", bbox=bbox, color=color, width_px=kw.pop("w", 2)); e.update(kw); return e
def R(bbox, **kw):
    e = dict(type="rect", bbox=bbox); e.update(kw); return e
def I(bbox, **kw):
    e = dict(type="image", bbox=bbox); e.update(kw); return e

def chapter(add, x=130):
    add.append(T("02", [x-4, 24, x+140, 116], color="#4A9BD5", bold=True, font_pt=40, wrap=False, name="chapter-number",
                 runs=[dict(text="0", color="#BFDDF0"), dict(text="2", color="#4A9BD5")]))
def pageno_odd(add, n):
    add.append(T(n, [1426, 2190, 1470, 2222], color=GRAY, bold=True, font_pt=12, name="page-number"))
    add.append(L([1408, 2195, 1410, 2220], color=GRAY, w=2, name="page-bar"))
def pageno_even(add, n):
    add.append(T(n, [179, 2200, 220, 2233], color=GRAY, bold=True, font_pt=12, name="page-number"))
    add.append(L([228, 2200, 230, 2230], color=GRAY, w=2, name="page-bar"))
def bluebox(add, bbox):
    add.append(R(bbox, line=BLUE, line_px=2, fill=None, name="highlight-frame", z=0))

OV = {}
# ---------------------------------------------------------------- page 1
add = []; chapter(add); pageno_odd(add, "35")
add.append(T("Chapter", [138, 66, 195, 84], color="#94BADC", font_pt=6))
bluebox(add, [300, 240, 1476, 411])
add += [L([132, 498, 915, 500]), L([132, 822, 1470, 825])]
for y in (543, 590, 637, 684, 730): add.append(L([132, y, 915, y+1], dash="dot", w=1))
add.append(R([131, 1428, 1470, 2150], gradient=["#E3F0F8", "#F9FCFE"], gradient_angle=90, name="diagram-bg", z=-1))
add.append(I([655, 1650, 960, 1985], name="spc-globe"))
add.append(I([556, 1505, 700, 1655], inpaint=[[622, 1512, 684, 1580], [578, 1587, 642, 1642]], name="arrow-equity"))
add.append(I([903, 1500, 1062, 1640], inpaint=[[903, 1503, 978, 1581], [974, 1577, 1025, 1627]], name="arrow-epc"))
add.append(I([443, 1784, 620, 1826], name="arrow-lease"))
add.append(I([975, 1786, 1150, 1828], name="arrow-loan"))
add.append(I([556, 1880, 706, 2058], inpaint=[[558, 1903, 648, 1983], [596, 1977, 683, 2056]], name="arrow-power"))
lab = dict(color="#6B6E6E", font_pt=9.5, align="center", wrap=False, rotation=315)
add += [T("배당", [620, 1529, 690, 1561], **lab), T("출자", [573, 1598, 643, 1630], **lab),
        T("대금지급", [885, 1524, 995, 1556], **lab), T("시공", [964, 1585, 1034, 1617], **lab),
        T("전력판매", [547, 1927, 657, 1959], **lab), T("대금지급", [585, 2000, 695, 2032], **lab)]
OV[1] = dict(
    delete=["i1", "i3", "i5", "i6", "i8", "i11", "i17", "i18", "r0", "l0", "l1", "l2", "l3", "l4", "l5", "l6", "t9"],
    set={
        "t0": dict(text="건설계획"),
        "t4": dict(text="• 한국도로공사가 보유한 성토부의 가용자산을 활용하여 신재생에너지 생산 및 전기 보급\n• “2050 탄소중립의 실천”, “국가온실가스감축목표(NDC)”의 신에너지 국가정책에 기여\n• 유휴자산을 활용하여 청정에너지 생산, 신수익 창출 및 신규 일자리 등 사회적 가치실현"),
        "t5": dict(color="#FFFFFF", bold=True),
        "t7": dict(text="사 업 명\n발 주 기 관\n사 업 방 식\n설 치 부 지\n설 치 용 량", bold=True),
        "t8": dict(text="2023년 고속도로 민간투자 태양광 발전사업\n한국도로공사\nBOT(Build-Operate-Transper)\n경기 평택시 칠괴동 42-1일원 외 14개소\n10MW"),
        "t10": dict(text="건설기간 : 실시협약 체결 후 18개월\n운영기간 : 건설기간 완료 후 20년"),
        "t11": dict(text="사 업 기 간", bold=True),
        "t15": dict(text="• “2050 탄소중립의 실천”의 정책실현\n• 청정그린에너지 생산으로 저탄소 탄소중립국가로 도약\n• 정부의 신재생에너지 보급정책에 기여"),
        "t16": dict(text="• 한국도로공사와 사업시행자의 공익사업 실현\n• 화석발전 대비 CO₂ 약 7천만톤 저감효과 기대\n• 신규 일자리 500개의 고용창출효과 기대"),
        "t19": dict(text="• 신에너지전환으로 국가온실가스감축목표(NDC) 실천\n• “환경오염 Zero” 목표로 친환경 발전소 건립\n• 경관이 우수하며 주변과 조화로운 발전소 건립"),
        "t20": dict(text="• 한국도로공사 유휴부지를 활용 신부가가치 창출\n• 본사업에 직접 지역주민을 참여 수익 공유\n• 유휴부지를 이용 환경친화적인 청정에너지 생산"),
        "t24": dict(text="전문\n건설업체", align="center"),
        "t25": dict(text="사업\n신청자", bbox=[404, 1540, 474, 1598], align="center", pitch_px=33),
        "t32": dict(text="운영\n및 유지관리", bbox=[736, 1787, 880, 1858], align="center", pitch_px=40, bold=True),
        "t38": dict(text="RE100\n기업", bbox=[1216, 2045, 1286, 2102], align="center", pitch_px=32, bold=False),
    }, add=add)
# ---------------------------------------------------------------- page 2
add = []; chapter(add, 165); pageno_even(add, "36")
add.append(L([259, 121, 322, 123], color="#558FC7", w=2))
add.append(R([166, 247, 1508, 313], fill="#D3DFE1", name="table-header"))
add += [L([166, 245, 1508, 247], color="#AEB2B2"), L([167, 362, 1510, 364], color="#AEB2B2"),
        L([262, 247, 264, 362], color="#C4C8C8", w=1), L([395, 247, 397, 362], color="#C4C8C8", w=1)]
add.append(I([163, 204, 197, 240], name="section-icon"))
add += [T("권역번호", [182, 268, 300, 298], bold=True, color="#2B2F2F", align="center"),
        T("사업규모", [318, 268, 427, 298], bold=True, color="#2B2F2F", align="center"),
        T("10,062.60", [318, 318, 440, 350], align="center"),
        T("서울", [592, 725, 662, 758], color="#565455", font_pt=10, bold=True),
        T("인천", [500, 780, 568, 812], color="#565455", font_pt=10, bold=True),
        T("경기도", [648, 815, 728, 848], color="#565455", font_pt=10, bold=True),
        T("울산", [1348, 1517, 1404, 1548], color="#565455", font_pt=10, bold=True),
        T("영동선", [1074, 1898, 1132, 1920], color="#565859", font_pt=8),
        T("중앙선\n2,490.00kW", [1411, 1945, 1502, 1987], color="#595B5C", font_pt=8, pitch_px=21),
        T("합    계", [770, 1915, 865, 1940], bold=True, color="#404143", align="center"),
        T("총 계", [1112, 1766, 1182, 1786], bold=True, color="#404143", align="center")]
s2 = {
    "t2": dict(text="전체 사업대상지 현황", bbox=[200, 206, 474, 239]),
    "t4": dict(text="권 역(행정소재)"),
    "t6": dict(text="경기도, 강원도, 충청북도, 충청남도, 서울특별시, 인천광역시, 대전광역시, 세종특별자치시", bbox=[462, 315, 1398, 352]),
    "t7": dict(bold=False),
    "t9": dict(text="중앙선", bbox=[920, 598, 992, 628]),
    "t11": dict(text="중부선", bbox=[796, 752, 862, 782]),
    "t12": dict(text="영동선", bbox=[895, 880, 963, 908]),
    "t13": dict(text="평택제천선", bbox=[714, 916, 834, 948], bold=True),
    "t14": dict(text="당진청주선", bbox=[390, 972, 507, 1003], bold=True),
    "t23": dict(text="충청남도", bbox=[508, 1160, 612, 1195]),
    "t29": dict(text="대구", bbox=[1118, 1398, 1200, 1432], color="#565455", bold=True, font_pt=10),
    "t31": dict(color="#FFFFFF"), "t32": dict(color="#FFFFFF"),
    "t53": dict(text="평택제천선 (13.45~13.6k)"),
    "t62": dict(text="경부선 (306.28~306.84k)", bbox=[698, 1741, 913, 1763]),
    "t70": dict(text="중부선\n433.80kW"), "t71": dict(text="평택 제천선\n652.80kW"),
    "t79": dict(text="서산 영덕선\n3,052.20kW", bbox=[1411, 1896, 1502, 1938], pitch_px=21),
    "t81": dict(text="984.60kW"), "t85": dict(text="서해안선\n999.60kW"),
    "t86": dict(text="중부선 (321.46~321.77k)"), "t97": dict(text="844.80kW"),
    "t98": dict(text="경부선\n1,863.00kW"), "t99": dict(text="당진 청주선\n1,831.20kW"),
    "t52": dict(text="7,746.00kW"), "t59": dict(text="2,490.00kW"), "t65": dict(text="12,307.20kW"),
    "t103": dict(text="서산영덕선 (31.28~31.47k)"),
    "i3": dict(transparent=False, name="map-and-tables"),
}
for t in "t44 t48 t49 t52 t54 t56 t59 t61 t63 t65 t67 t69 t73 t76 t87 t89 t97 t101 t104 t53 t44".split():
    s2.setdefault(t, {})["bold"] = False
OV[2] = dict(delete=["i0", "i1", "i2", "r1", "t5", "t8", "t16", "t18", "t19", "t20", "t21", "t27", "t28",
                     "t45", "t74", "t82", "t92", "t95", "t100", "t90", "t91"], set=s2, add=add)
# ---------------------------------------------------------------- page 3
add = []; pageno_odd(add, "37")
for (x0, x1, ys) in ((252, 517, ((422, 608), (622, 810), (824, 1019))), (926, 1190, ((420, 614), (624, 817), (826, 1022)))):
    for k, (y0, y1) in enumerate(ys): add.append(I([x0, y0, x1, y1], photo=True, name=f"disaster-photo-{x0}-{k}"))
add += [T("1. 건설안전 관리", [136, 190, 400, 226], bold=True, color="#2F3131"),
        T("1.1 건설 중 발생 가능한 각종 재난,사고 등 위험요소 분석", [136, 246, 891, 283], bold=True, color="#2F3131"),
        T("(1) 건설 중 발생 가능한 각종 재난", [136, 298, 620, 334], color="#2F3131")]
add += [T("• 성토 구조물, 패널 유실\n• 설비 불량 발생\n• 근로자 안전사고\n• 감전사고 유발", [532, 446, 785, 586], pitch_px=35),
        T("화    재\n산    불", [826, 485, 914, 551], bold=True, color="#373A39", pitch_px=40),
        T("교    통\n재    난", [826, 688, 914, 753], bold=True, color="#373A39", pitch_px=40),
        T("추    락\n붕    괴", [825, 890, 913, 957], bold=True, color="#373A39", pitch_px=40)]
# table frames / lines (top two tables)
add += [L([136, 611, 800, 613]), L([136, 814, 800, 816]), L([136, 1020, 800, 1022]), L([136, 408, 138, 1022]), L([798, 408, 800, 1022]),
        L([808, 617, 1473, 619]), L([808, 820, 1473, 822]), L([808, 1024, 1473, 1026]), L([808, 412, 810, 1026]), L([1471, 412, 1473, 1026])]
# chart as one image, right stats table rebuilt
add.append(I([131, 1117, 797, 1610], transparent=False, name="accident-chart"))
add.append(R([805, 1117, 1470, 1610], line=LINE, line_px=2, fill=None, name="stats-frame"))
cols = [812, 941, 1074, 1200, 1330, 1465]
def row(y0, y1, vals, bold=False):
    for k, v in enumerate(vals): add.append(T(v, [cols[k]+4, y0, cols[k+1]-4, y1], align="center", bold=bold, color="#3D3F40"))
for y in (1232, 1362, 1488): add.append(R([812, y, 1465, y+32], fill="#EEF0EA", z=0))
for y in (1264, 1302, 1394, 1430, 1520, 1557): add.append(L([812, y, 1465, y+1], w=1))
add += [T("• 신재생에너지원별 생애주기", [826, 1193, 1137, 1220], bold=True, color="#484A49"), T("(단위 : 명)", [1355, 1196, 1454, 1220], align="right"),
        T("• 신재생에너지원별 발생형태", [825, 1320, 1137, 1347], bold=True, color="#484A49"), T("(단위 : 명)", [1354, 1323, 1453, 1347], align="right"),
        T("• 신재생에너지원별 기인물현황", [825, 1447, 1163, 1475], bold=True, color="#484A49"), T("(단위 : 명)", [1353, 1451, 1453, 1477], align="right")]
row(1236, 1262, ["설치", "제조", "유지보수", "분류불능", "합 계"], True); row(1276, 1300, ["23", "1", "5", "1", "30"])
row(1365, 1392, ["추락사", "익사", "끼임", "감전 등", "합 계"], True); row(1404, 1428, ["26", "1", "1", "2", "30"])
row(1491, 1518, ["지붕", "사다리", "전주", "기타(비계등)", "합 계"], True); row(1531, 1555, ["20", "2", "2", "6", "30"])
for y in (1757, 1800, 1843): add.append(L([624, y, 1467, y+1], dash="dot", w=1))
OV[3] = dict(
    delete=["i0", "i1", "i2", "i5", "i6", "i7", "i8", "i9", "i10", "i11", "i12", "i13", "i14", "i15", "i16", "i17", "i18", "i19", "i20", "i21",
            "r0", "r3", "r4", "r5", "l0", "l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8", "l9", "l10", "l11", "l16", "l17", "l18", "l19", "l20", "l21", "l22",
            "t2", "t10", "t11", "t12", "t16", "t34", "t35", "t37", "t51", "t56", "t61"] +
           [f"t{k}" for k in range(22, 51) if k not in (34, 35, 37, 41, 42, 43, 44, 45, 49)],
    set={
        "t1": dict(text="발전사업"),
        "t5": dict(text="• 공사현장 화재 파급\n• 자재 및 시설물 손상\n• 근로자 안전사고\n• 감전사고 유발"),
        "t7": dict(text="• 구조물 피로 증대\n• 감전사고 유발\n• 각종 시설물 손상\n• 전기자재 절연력 약화"),
        "t9": dict(text="폭    염\n대    설", bbox=[152, 682, 238, 748], bold=True, color="#373A39"),
        "t6": dict(bold=True, color="#373A39"),
        "t13": dict(text="• 화재사고 유발\n• 근로자 안전사고\n• 구조물 변형 불량\n• 각종 시설물 손상"),
        "t14": dict(text="• 근로자 추락사고\n• 공사장 낙하물사고\n• 구조물 변형 불량\n• 기자재 파손", bbox=[1204, 856, 1424, 995]),
        "t15": dict(text="낙    뢰\n지    진", bbox=[152, 885, 238, 951], bold=True, color="#373A39"),
        "t17": dict(text="(2) 태양광 공사현장 사고"),
        "t18": dict(text="사망사고 현황"),
        "t49": dict(text="➜ 태양광 공사현장 사망사고의 86.7%는 추락사로서\n   이에 대한 안전계획을 수립함", bbox=[190, 1523, 752, 1589], pitch_px=38, bold=True),
        
        "t54": dict(text="발 생 일 시\n발 생 위 치\n피 해 규 모\n관 할 기 관", bold=True, color="#3D3F40"),
        "t55": dict(text="2023년 4월 29일 밤 11시 30분경\n인천광역시 서구 원당동 검단신도시 안단테 아파트 신축 현장\n지하주차장 2개층 지붕 구조물 총 970㎡ 파손\n인천광역시 서구청, 인천경찰청"),
        "t57": dict(text="지하주차장 1층 지붕층인 어린이 놀이터 예정\n지점과 지하주차장 2층의 지붕층이 연쇄적으로 붕괴"),
        "t58": dict(text="발 생 상 황", bold=True, color="#3D3F40"),
        "t59": dict(text="• 설계·감리·시공 등 총체적 부실로 인한 전단보강철근의 미설치\n• 붕괴구간 콘크리트 강도부족 등 품질관리 미흡\n• 공사과정에서 추가되는 하중을 적게 고려\n• 골조가 완료될 때까지 지하주차장 정기안전점검을 미실시"),
        "t60": dict(text="발 생 원 인", bold=True, color="#3D3F40"),
        "l12": dict(bbox=[624, 1700, 1467, 1703]), "l13": dict(bbox=[624, 1891, 1467, 1893]), "l14": dict(bbox=[623, 1981, 1467, 1983]),
        "i3": dict(name="collapse-photo"),
    }, add=add)
# ---------------------------------------------------------------- page 4
add = []; chapter(add, 165); pageno_even(add, "38")
add += [T("1.2 각종 재난사고 등 위험요소에 대한 안전조치 계획", [164, 205, 861, 246], bold=True, color="#2F3131"),
        T("(1) 건설 중 발생하는 각종재난에 대한 안전조치 계획", [164, 255, 861, 296], color="#2F3131")]
for k, (y0, y1) in enumerate(((1146, 1300), (1315, 1462), (1470, 1625), (1637, 1798))): add.append(I([170, y0, 450, y1], photo=True, name=f"site-photo-{k}"))
add.append(R([164, 1091, 1512, 1154], fill="#D6E2E3", name="table2-header"))
for y in (367, 528, 689, 850, 1010): add.append(L([164, y, 1512, y+2], color="#B8BCBC"))
for y in (1307, 1465, 1627, 1789): add.append(L([164, y, 1512, y+2], color="#B8BCBC"))
add += [L([581, 367, 583, 1012], color="#C4C8C8", w=1), L([894, 367, 896, 1012], color="#C4C8C8", w=1),
        L([452, 1154, 454, 1791], color="#C4C8C8", w=1), L([896, 1154, 898, 1791], color="#C4C8C8", w=1)]
add.append(R([166, 1141, 1514, 1307], line="#F48C5A", line_px=4, fill=None, name="highlight-orange"))
add += [T("• 인명 및 재산상 손실\n• 강구조물 및 패널 유실\n• 감전 및 근로자 안전사고", [594, 388, 880, 500], pitch_px=39),
        T("• 사고대책본부 가동 및 2차사고 예방대책 수립\n• 피해복구계획 수립 및 필요시 현장 철거\n• 침수 및 파손자재 확인 후 복구 및 재시공", [907, 383, 1420, 503], pitch_px=40),
        T("낙    뢰\n지    진", [178, 575, 289, 645], bold=True, color="#343637", pitch_px=40),
        T("• 인명 및 재산상 손실\n• 수배전반 등의 손상\n• 감전 및 근로자 안전사고", [594, 549, 880, 664], pitch_px=39),
        T("• 사고대책본부 가동 및 근로자 안전대책 확보\n• 피해복구계획 수립 및 필요시 현장 철거\n• 써지침입설비 및 파손자재 확인 후 교체", [907, 544, 1420, 664], pitch_px=40),
        T("화    재\n산    불", [178, 735, 289, 805], bold=True, color="#343637", pitch_px=40),
        T("• 인명 및 재산상 손실\n• 공사현장 시설물 화재\n• 감전 및 근로자 안전사고", [594, 710, 880, 825], pitch_px=39),
        T("• 구조물 변형 등 원인파악 및 피해규모 분석\n• 피해복구계획 수립 및 필요시 현장 철거\n• 피해지역 재시공 및 지체일수 등 전체 공정계획 수립", [907, 705, 1490, 825], pitch_px=40),
        T("기    타\n사    회\n재    난", [178, 875, 294, 985], bold=True, color="#343637", pitch_px=38),
        T("• 감염병(코로나19) 발생\n• 교통재난 발생\n• 기타 비상 국가 재난 시", [596, 870, 880, 985], pitch_px=39)]
for bb in ([177, 1890, 672, 2018], [177, 2034, 672, 2162], [1023, 1885, 1512, 2010], [1023, 2030, 1512, 2156]):
    add.append(R(bb, line="#D5DBE2", line_px=2, fill=None, rounded=True, radius=0.08, name="note-frame"))
OV[4] = dict(
    delete=["i0", "i4", "i5", "i6", "i7", "i8", "i11", "i12", "i13", "i14", "i15", "i16", "i17", "i18", "i19", "i20", "i21",
            "l2", "l4", "l5", "l9", "l10", "l11", "l12", "l13", "l14", "l15", "l16", "l17", "l18",
            "t2", "t6", "t7", "t9", "t10", "t11", "t12", "t13", "t15", "t16", "t17", "t24", "t29"],
    set={
        "t8": dict(bold=True, color="#343637"),
        "t14": dict(text="• 근로자 안전대책 강구 및 대체인력 확보\n• 우회 도로 및 교통수단 확보로 자재수급 확인\n• 국가 재난메뉴얼 이행 및 비상체제 돌입"),
        
        "t22": dict(text="• 가드라인 안전대에 안전후크를 걸고 작업\n• 작업반경내 접근금지 및 아웃트리거 최대 인출\n• 작업중량 , 허용재원 및 안전메뉴얼 준수"),
        "t23": dict(text="• 고소작업 중 인적 낙하사고\n• 모듈 구조물 양중시 물적 낙하사고\n• 크레인, 굴착기 전도사고"),
        "t26": dict(text="• 기계장비, 운전 미숙에 의한 자재파손\n• 기자재 정비불량에 의한 오작동\n• 소자재 비탈면 이동 시의 안전사고"),
        "t27": dict(text="• 공정지연 예방을 위한 도난자재 긴급발주 시행\n• CCTV 등 공사현장 방범설비 및 시건장치 강화보수\n• 가드휀스 선시공하여 기자재 및 주요장비 보호"),
        "t28": dict(text="• 모듈 및 인버터 등 기자재 도난사고\n• 장비 및 현장차량 파손사고\n• 준공전 기시공분 파손 및 도난사고"),
        "t30": dict(text="• 작물 수매, 축산물 매입 등 적정 보상대책 시행\n• 오염원 발생 작업 시 주변 경작물 방호조치 시행\n• 주요자재는 일몰 후 및 일출 전 운반 현장적치"),
        "t31": dict(text="• 인근 경작물 오염 및 훼손 사고\n• 공사 중 소음으로 인한 가축 피해\n• 작업차량과 농기계의 교통사고"),
        "t33": dict(text="• 공법변경시 원설계사 의견 청취 및 확인\n• 재하도 금지, 사업시행자 직접 관리\n• 크레인, 굴착기 정격하중 및 사용메뉴얼 준수"),
        "t37": dict(text="• 비상연락체계 및 “안전사고대응메뉴얼” 시험훈련\n• 본사지원팀 현장일지,감리일지의 위험요소 관리\n• 고속도로 인접구간 시공전 관할지사 사전협의"),
        "t35": dict(align="center", bold=True, color="#2F3030"), "t36": dict(align="center", bold=True, color="#2F3030"),
        "t39": dict(align="center", bold=True, color="#2F3030"), "t40": dict(align="center", bold=True, color="#2F3030"),
        "t41": dict(text="38", bbox=[179, 2204, 215, 2238]),
        "i22": dict(name="management-circles"),
    }, add=add)
OV[4]["add"] = [a for a in add if a.get("name") != "page-number"]
# ---------------------------------------------------------------- page 5
add = []; pageno_odd(add, "39")
bluebox(add, [300, 241, 1476, 408])
add += [R([129, 417, 791, 470], fill="#D5E0E1", name="table-header"),
        R([130, 470, 300, 597], fill="#F0824A", name="row1-label-bg"),
        R([130, 470, 797, 597], line="#EF9662", line_px=3, fill=None, name="row1-frame"),
        L([129, 597, 791, 599]), L([129, 713, 791, 715]), L([129, 830, 791, 832]),
        T("방지대책", [455, 430, 560, 460], bold=True, color="#2F3231"),
        T("• 모듈, 구조물 양중 시 고속도로 하향 양중\n• 크레인 작업반경내 입출입 통제\n• 크레인 작업중량 및 허용재원 준수", [318, 480, 785, 590], pitch_px=38),
        T("교 통 사 고", [142, 634, 298, 664], bold=True, color="#393C3D"),
        T("• 작업 전 작업특성에 맞는 안전교육 실시\n• 작업자 고속도로 접근금지, 안전요원 배치\n• 부체도로 통행을 위한 3.0m의 최소폭원 유지", [318, 600, 785, 710], pitch_px=38),
        T("• 2인1조 작업, 자발적 위험인식 함양 교육\n• 굴착기는 전도예방을 위한 트랙식장비 사용\n• 소형자재도 가급적 크레인, 굴착기 운반", [318, 718, 785, 828], pitch_px=38),
        R([990, 490, 1113, 538], line="#3FADE3", line_px=2, fill="#FFFFFF", name="box-simple-accident"),
        L([1051, 540, 1051, 600], color="#8A8F90", arrow_end=True), L([1222, 541, 1222, 600], color="#8A8F90", arrow_end=True),
        L([988, 650, 946, 650], color="#8A8F90", arrow_end=True), L([1286, 652, 1330, 652], color="#8A8F90", arrow_end=True, arrow_start=True),
        I([805, 1858, 1140, 1990], name="ppe-worker-icon"),
        T("• 작업구역 안전 사고 예방\n• 차량통제 및 보행사고\n   예방", [1140, 1873, 1430, 1981], pitch_px=36),
        R([126, 2012, 1462, 2152], line=LINE, line_px=2, fill=None, name="note-frame"),
        T("인적, 물적낙하", [144, 517, 298, 546], color="#FFFFFF", bold=True),
        T("사고형태", [167, 430, 271, 459], color="#2F3231", bold=True)]
for bb, nm in (([128, 1394, 1466, 1595], "card-1"), ([128, 1595, 793, 1797], "card-2"), ([800, 1600, 1465, 1800], "card-3"),
               ([127, 1797, 792, 1990], "card-4"), ([800, 1802, 1464, 1995], "card-5")):
    add.append(R(bb, line=LINE, line_px=2, fill=None, name=nm))
OV[5] = dict(
    delete=["i0", "i2", "i15", "i16", "i17", "l0", "l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8", "l9", "l10", "l11", "l12", "l13", "l14", "l21",
            "t6", "t20", "t21", "t22", "t23", "t24", "t28", "t35", "t37", "t38", "t39"],
    set={
        "t1": dict(text="발전사업"),
        "t3": dict(text="• 고속도로 주행차량의 안전에 영향이 없도록, 고속도로와 이격하여 부체도로에서 공사수행\n• 부체도로를 통행하는 주민, 농민의 안전사고 예방을 위하여 농한기 시공계획 수립\n• 공사구간내 안전을 위하여 안전관리자 통제하에 작업 수행"),
        "t4": dict(text="중점사항", color="#FFFFFF", bold=True),
        "t7": dict(color="#FFFFFF"), "t8": dict(align="center"), "t9": dict(align="center"),
        "t10": dict(text="대표이사\n보고", bbox=[1357, 467, 1429, 515], align="center", bold=False),
        "t12": dict(text="인적, 물적낙하", color="#FFFFFF", bold=True),
        "t13": dict(align="center"), "t14": dict(align="center"),
        "t17": dict(text="• 현장책임자 안전교육 이수(전기안전관리법 25조)\n• 작업팀은 도로차단 안전관리계획서를 별도 제출\n• 인명사고 시 119 신고 선조치 후 보고"),
        "t18": dict(bold=True),
        "t25": dict(text="① 교통안내 표지판 설치"), "t29": dict(text="② 공사안내 표지판 설치", bbox=[325, 1613, 602, 1642]),
        "t30": dict(text="③ PE드럼 러버콘, 윙카 설치", bbox=[970, 1617, 1300, 1646]),
        "t33": dict(text="④ 자재운반 사다리차 작업"), "t34": dict(text="⑤ 안전요원 배치", bbox=[1040, 1818, 1230, 1846]),
        "t26": dict(text="• 공사구간 전방 설치\n• 부체도로 통행자 사전 인지\n• 각 필요 위치별로 설치"),
        "t27": dict(text="• 공사구간 전방 설치\n• 부체도로 통행자 사전 인지\n• 작업구역에 따라 수시 이동"),
        "t31": dict(text="• 공사구간 전방 설치\n• 부체도로 통행자 사전인지\n• 공사내용 전반에 대하여 명기"),
        "t36": dict(text="• 성토비탈면 자재 인양\n• 전도사고 유의\n• 철재구조물 등 운반"),
        "t40": dict(text="• 관련표지 설치 후 운전자가 통행방법을 이해하지 못하거나, 안전문제가 발생(예상) 될 경우 즉시 수정 후 재설치\n• 기존 표지와 도로 공사구간 주의표지 내용이 다를 경우 기존 표지를 가리거나 임시로 제거\n• 가급적 작업보호 자동차를 2대 이상 배치하며, 작업 활동구역과 최소 60m 이상 이격하여 배치"),
        "i8": dict(transparent=False, name="site-aerial-photo"),
    }, add=add)
# ---------------------------------------------------------------- page 6
add = []; chapter(add, 165); pageno_even(add, "40")
add.append(L([259, 119, 322, 121], color="#558FC7", w=2))
add.append(R([335, 247, 1510, 412], line=BLUE, line_px=2, fill=None, name="highlight-frame", z=0))
add.append(I([163, 418, 1512, 830], transparent=False, name="safety-infographic"))
add.append(I([170, 975, 840, 1530], transparent=False, name="org-chart"))
add.append(T("중점\n교육", [905, 1105, 978, 1180], bold=True, color="#2F3131", align="center", font_pt=12, pitch_px=40))
add.append(I([1078, 1220, 1212, 1306], name="management-circle"))
add += [T("정 기 교 육", [868, 1340, 1090, 1368], bold=True, color="#303232"), T("• 안전작업방법 지도요령", [1110, 1340, 1400, 1368]),
        T("일 상 교 육", [868, 1383, 1090, 1411], bold=True, color="#303232"), T("• 대피요령 및 위험요소", [1110, 1383, 1400, 1411]),
        T("특 별\n교 육", [868, 1428, 938, 1500], bold=True, color="#303232", align="center", pitch_px=44),
        T("취 약 시 기", [955, 1428, 1090, 1456], bold=True, color="#303232"), T("• 계절별 특성 안전사항", [1110, 1428, 1400, 1456]),
        T("위 험 예 지", [955, 1472, 1090, 1500], bold=True, color="#303232"), T("• 당일작업 위험사항", [1110, 1472, 1400, 1500]),
        L([856, 1318, 1500, 1320]), L([856, 1375, 1500, 1377], w=1), L([856, 1420, 1500, 1422], w=1), L([856, 1465, 1500, 1467], w=1),
        L([945, 1422, 947, 1510], w=1), L([1098, 1330, 1100, 1510], w=1)]
add.append(I([222, 1615, 458, 1900], transparent=False, name="daily-check-pie"))
for k, (x0, x1, nm) in enumerate(((190, 351, "안전의날 행사"), (360, 515, "안전보건협의회"), (524, 679, "정기안전점검"), (688, 828, "총괄안전점검"))):
    add.append(T(nm, [x0, 2001, x1, 2030], color="#FFFFFF", bold=True, align="center", font_pt=9, bg="#6684A1", mask="fill"))
add += [T("시설물 점검 및\n공종별\n점검 실시\n(월 1회 실시)", [530, 2045, 672, 2142], align="center", color="#535454", pitch_px=24),
        T("현    장", [940, 1818, 1080, 1850], color="#FFFFFF", bold=True, align="center"),
        T("사고발생", [996, 1660, 1096, 1688], color="#FFFFFF", bold=True, bg="#179D9A", mask="fill"),
        R([864, 1950, 1164, 2150], line="#A9CCE9", line_px=2, fill=None, rounded=True, radius=0.06, name="after-frame"),
        R([1209, 1948, 1510, 2146], line="#A9CCE9", line_px=2, fill=None, rounded=True, radius=0.06, name="onsite-frame")]
for bb, nm in (([170, 905, 840, 1535], "sec-org"), ([845, 905, 1512, 1535], "sec-edu"), ([174, 1540, 841, 2170], "sec-check"), ([850, 1540, 1516, 2170], "sec-emergency")):
    add.append(R(bb, line=LINE, line_px=2, fill=None, name=nm, z=-1))
OV[6] = dict(
    delete=["i1", "i2", "i3", "i4", "i5", "i6", "i7", "i9", "i10", "i11", "i13", "i14", "i16", "i17", "i18", "i19", "i21", "i22",
            "r5", "r7", "r8", "r9", "r10", "r11", "r12", "r13", "l0", "l1", "l2", "l3", "l4", "l7", "l8", "l9", "l10", "l11", "l12", "l13", "l14", "l15",
            "t12", "t37", "t38", "t40", "t46", "t47", "t48", "t49", "t50", "t52", "t53", "t55", "t56", "t57", "t58", "t59", "t60", "t62", "t63", "t65",
            "t66", "t67", "t68", "t71", "t72", "t73", "t74", "t75", "t76", "t82", "t83", "t84"],
    set={
        
        "t3": dict(text="• 사업시행자는 본 사업이 안전하게 건설될 수 있도록 안전관리조직을 구성하며 전직원에게 R&R 부여\n• 정기적, 일상적인 안전교육 및 안전점검을 실시하여 안전사고예방에 선제적으로 대처\n• 사고, 재난 기상이변에 즉각적인 대처를 위하여 비상 시 긴급조치를 수립하고 수시 점검훈련 실시"),
        "t4": dict(color="#FFFFFF", bold=True),
        "t5": dict(color="#FFFFFF", mask="inpaint"), "t6": dict(color="#FFFFFF", mask="inpaint"), "t15": dict(color="#FFFFFF", mask="inpaint"), "t16": dict(color="#FFFFFF", mask="inpaint", bbox=[197, 784, 293, 812]),
        "t7": dict(text="정기, 일상 및 특별교육으로 안전의 일상화", bbox=[1019, 489, 1470, 518], align="right"),
        "t8": dict(text="공사조직원에 안전에 관한 R&R 부여", bbox=[219, 496, 599, 525]),
        "t9": dict(text="안전지침,환경관리 사고사례 등을 분석 및 사례고찰\n안전관리계획 이행보고 계획 수립", align="right", bbox=[973, 528, 1470, 594]),
        "t10": dict(text="안전관리, 재해, 공사장 주변안전 등 안전제일주의\n사업시행자 및 협력업체를 포함한 전임직원 대상"),
        "t11": dict(text="“No Safety\nNo Work”", bbox=[740, 588, 940, 662], align="center", bold=True, color="#292D33"),
        "t13": dict(text="사고,재난,기상이변에 대한 즉각적인 대처\n비상연락망, 비상동원, 경보체계 구축 수시 점검훈련\n자발적인 참여유도로 안전자립 구축", align="right", bbox=[970, 647, 1470, 752]),
        "t14": dict(text="정기점검, 일상점검 및 총괄점검 수행\n개인자체점검, 합동점검 전임직원 대상\n선제적 점검으로 안전사고 사전예방"),
        "t41": dict(color="#FFFFFF"), "t42": dict(text="“ No Safety No Work ”"),
        "t51": dict(color="#FFFFFF"),
        "t54": dict(text="• 사고발생 후 확산방지\n   응급조치\n• 유관부서 협조요청\n• 단전,단수 등에 따른\n   응급조치 실시\n• 필요시 차량통제 및\n   우회조치"),
        "t77": dict(text="• 현장 비상관리 조직 가동\n• 담당조직별 구난활동 실시\n• 원상복구 및 사고현장\n   주변정리"),
        "t80": dict(text="우수근로자,\n협력사 시상 및\n안전교육 및\n공지사항"), "t81": dict(text="안전점검에 따른\n문제점들의\n토의 및 검토"),
        "i0": dict(name="accident-box"), "i20": dict(bbox=[555, 1625, 765, 1845]),
    }, add=add)
for p, ov in OV.items():
    json.dump(ov, open(f"overrides/p{p}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("overrides written:", sorted(OV))
