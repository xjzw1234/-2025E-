"""Build the MCM/ICM Word paper from frozen results and figures (revised layout)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SKILL = Path(r"C:\Users\ASUS\.claude\skills\math-modeling")
sys.path.insert(0, str(SKILL / "tools" / "docx" / "scripts"))

import paper_format as pf  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402

_orig_font = pf.set_run_font


def _font(run, font="Times New Roman", size=12, bold=False):
    _orig_font(run, "Times New Roman", size, bold)


pf.set_run_font = _font

FIG = ROOT / "figures"
RES = ROOT / "results"

UNIT_MAP = [
    ("m^2 gC^-1 d^-1", "m² gC⁻¹ d⁻¹"),
    ("g C m^-2", "g C m⁻²"), ("g N m^-2", "g N m⁻²"),
    ("mg a.i. kg^-1", "mg a.i. kg⁻¹"),
    ("kg ha^-1", "kg ha⁻¹"), ("CNY ha^-1", "CNY ha⁻¹"),
    ("d^-1", "d⁻¹"), ("m^2", "m²"), ("m^3", "m³"),
    ("S_N", "SN"), ("X_H", "XH"), ("X_P", "XP"),
    ("H_50", "H50"), ("r_C", "rC"), ("K_C", "KC"), ("r_W", "rW"),
    ("a_HC", "aHC"), ("a_BH", "aBH"), ("a_OB", "aOB"),
    ("f_N", "fN"), ("K_N", "KN"), ("sigma_C", "σC"),
    ("psi_B", "ψB"), ("nu_B", "νB"),
    ("rho_f", "ρf"), ("rho_y", "ρy"), ("lambda_poll", "λpoll"),
    ("DT50_H", "DT50,H"), ("DT50_P", "DT50,P"),
    ("kappa_lit", "κlit"), ("kappa_w", "κw"), ("kappa_D", "κD"),
    ("H_I", "HI"), ("Harvest rate eta", "Harvest rate η"),
    ("f_C", "fC"), ("phi_CN", "φCN"), ("u_H", "uH"), ("u_P", "uP"),
    ("U_N", "UN"), ("u_M", "uM"), ("u_org", "uorg"), ("u_F", "uF"), ("u_E", "uE"), ("u_B", "uB"), ("Pi_R", "ΠR"), ("Pi_O", "ΠO"), ("I_lit", "Ilit"),
    ("H_W", "HW"), ("S_W", "SW"), ("g_HW", "gHW"), ("g_HC", "gHC"),
]


def U(text):
    for a, b in UNIT_MAP:
        text = text.replace(a, b)
    return text


def add_page_numbers():
    from docx.enum.text import WD_ALIGN_PARAGRAPH as _A
    footer = DOC.sections[0].footer
    par = footer.paragraphs[0]
    par.alignment = _A.CENTER
    run = par.add_run()
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE"
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1); run._r.append(it); run._r.append(f2)
    pf.set_run_font(run, size=9)


def _fix_styles():
    for name in ("Heading 1", "Heading 2"):
        try:
            st = DOC.styles[name]
            st.paragraph_format.page_break_before = False
            st.paragraph_format.keep_with_next = True
        except KeyError:
            pass


PENDING_BREAK = [False]


def PAGEBREAK():
    PENDING_BREAK[0] = True


def H1(text):
    pf.heading1(DOC, text)
    para = DOC.paragraphs[-1]
    para.paragraph_format.page_break_before = PENDING_BREAK[0]
    PENDING_BREAK[0] = False
    para.paragraph_format.keep_with_next = True


def H2(text):
    pf.heading2(DOC, text)
    para = DOC.paragraphs[-1]
    para.paragraph_format.page_break_before = False
    para.paragraph_format.keep_with_next = True


def P(text, first_line=True):
    pf.paragraph(DOC, U(text), first_line=first_line, line_spacing=1.10)


def PS(text):
    """Short standalone paragraph without first-line indent."""
    pf.paragraph(DOC, U(text), first_line=False, line_spacing=1.15)


def EQ(latex, tag=None):
    from docx.enum.text import WD_TAB_ALIGNMENT
    pf.equation(DOC, latex)
    para = DOC.paragraphs[-1]
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for mr in para._p.iter(qn("m:r")):
        rpr = mr.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            mr.insert(0, rpr)
        sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "18"); rpr.append(sz)
        szcs = OxmlElement("w:szCs"); szcs.set(qn("w:val"), "18"); rpr.append(szcs)
    if tag is not None:
        para.paragraph_format.tab_stops.add_tab_stop(pf.Cm(15.6), WD_TAB_ALIGNMENT.RIGHT)
        run = para.add_run("	(%d)" % tag)
        pf.set_run_font(run, size=10)


def FIGURE(name, caption, width=14.0):
    pf.image(DOC, str(FIG / name), width_cm=width)
    pf.figure_caption(DOC, U(caption))


def TABLE(rows, caption, merges=None):
    cap = pf.figure_caption(DOC, U(caption))
    cap.paragraph_format.keep_with_next = True
    table = pf.three_line_table(DOC, [[U(str(c)) for c in row] for row in rows])
    if merges:
        for r, c1, c2 in merges:
            table.cell(r, c1).merge(table.cell(r, c2))
    header_rows = (0, 1) if merges else (0,)
    for r in header_rows:
        if r >= len(table.rows):
            continue
        for cell in table.rows[r].cells:
            paras = cell.paragraphs
            if len(paras) > 1:
                for extra in paras[1:]:
                    if not extra.text.strip():
                        extra._element.getparent().remove(extra._element)
            for par in cell.paragraphs:
                for run in par.runs:
                    run.font.bold = True
    last = len(table.rows) - 1
    for r, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        for cell in row.cells:
            for par in cell.paragraphs:
                par.paragraph_format.keep_with_next = r < last
                par.paragraph_format.space_before = pf.Pt(1)
                par.paragraph_format.space_after = pf.Pt(1)
                for run in par.runs:
                    run.font.size = pf.Pt(9.5)


TOC_ENTRIES = [
    (1, "Summary"),
    (1, "1. Introduction"),
    (1, "2. Assumptions and Notation"),
    (1, "3. Model Formulation"),
    (2, "3.1 Two timescales"),
    (2, "3.2 Seasonal forcing and the agricultural cycle"),
    (2, "3.3 Feeding fluxes and functional responses"),
    (2, "3.4 The full dynamical system"),
    (2, "3.5 Chemical fate"),
    (2, "3.6 Stability metrics"),
    (2, "3.7 Parameterization"),
    (1, "4. Question 1: Chemical Stress and Seasonality"),
    (2, "4.1 Design of the chemical grid"),
    (2, "4.2 Seasonal trajectories"),
    (2, "4.3 Yield and pest response"),
    (2, "4.4 Stability of the seasonal cycle"),
    (1, "5. Question 2: Edge Maturation and Species Return"),
    (2, "5.1 Two returning species"),
    (2, "5.2 Production and stability trade-off"),
    (2, "5.3 Stability after species return"),
    (1, "6. Question 3: Herbicide Withdrawal, Bats and Alternatives"),
    (2, "6.1 The withdrawal experiment"),
    (2, "6.2 The bat counterfactual"),
    (2, "6.3 Channel ablation"),
    (2, "6.4 Alternative species"),
    (1, "7. Question 4: Organic Portfolios"),
    (2, "7.1 Decision space and objectives"),
    (2, "7.2 Pareto front and knee point"),
    (2, "7.3 Six impact categories"),
    (2, "7.4 Component effects"),
    (1, "8. Validation and Sensitivity"),
    (2, "8.1 Numerical validation"),
    (2, "8.2 Limitations"),
    (2, "8.3 Sensitivity"),
    (1, "9. Discussion"),
    (2, "9.1 What limits the system"),
    (2, "9.2 From results to practice"),
    (2, "9.3 Model evaluation"),
    (1, "10. Letter to a Farmer"),
    (1, "References"),
    (1, "AI Use Report"),
]


def add_toc(pages_map=None):
    from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
    pages_map = pages_map or {}
    for level, item in TOC_ENTRIES:
        p = DOC.add_paragraph()
        p.paragraph_format.space_before = pf.Pt(0)
        p.paragraph_format.space_after = pf.Pt(1 if level == 2 else 2)
        if level == 2:
            p.paragraph_format.left_indent = pf.Cm(0.6)
        p.paragraph_format.tab_stops.add_tab_stop(
            pf.Cm(15.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        run = p.add_run(item)
        pf.set_run_font(run, size=10 if level == 2 else 11, bold=(level == 1))
        run2 = p.add_run("\t" + str(pages_map.get(item, "")))
        pf.set_run_font(run2, size=10 if level == 2 else 11)


PAGES_MAP = {}


def build():
    global DOC
    DOC = pf.new_document(contest="mcm-icm")
    _fix_styles()
    add_page_numbers()

    # ================= title & summary =================
    pf.title(DOC, "Making Room for Agriculture: A Seasonally Forced Food-Web Model "
                  "for Forest-to-Farm Transitions")
    pf.paragraph(DOC, "2025 ICM Problem E", align=WD_ALIGN_PARAGRAPH.CENTER)
    H1("Summary")
    P("A forest cleared for cropland loses the mature food web that once buffered it. Its "
      "replacement is a sequence of ecological states: weeds and pests colonize first, natural "
      "enemies follow their prey, edge vegetation thickens, and native species return at "
      "different speeds. Farmers act inside this sequence. They spray, fertilize, mow and "
      "harvest, and each decision changes the state that the next season starts from. We model "
      "this transition with one seasonally forced food web that is extended, not replaced, as "
      "the questions move from the initial agricultural community to species return, herbicide "
      "withdrawal and organic portfolios.")

    P("In the chemical grid for the oilseed crop, raising herbicide intensity from 0 to 1 with insecticide fixed at 0 "
      "reduced weed biomass from 12.12 to 8.94 g C m^-2. With herbicide fixed at 0, raising "
      "insecticide intensity from 0 to 1 reduced pest biomass from 3.07 to 2.18 g C m^-2 and "
      "predators from 0.66 to 0.46 g C m^-2. The full-treatment corner reached 1.98 and 0.42 and "
      "gave the highest yield, 3688 kg ha^-1 against 3506 without inputs. The pest coefficient of "
      "variation rose from 1.90 to 2.42 along the same path. The cycle stayed stable, with a "
      "Floquet radius of 0.576 and a recovery time of 661 days.")

    P("Earthworms raised yield by 1.05%, while raptors lowered it by 5.3% by suppressing bats and "
      "releasing pests; introducing both was 9.1% below the no-return baseline and 4.0% below the raptor-only case. After herbicide "
      "withdrawal, weeds rose from 8.01 to 9.63 g C m^-2 and yield held near 3153 kg ha^-1. "
      "Bat houses raised yield to 4783 kg ha^-1 and cut pest biomass to 1.17 g C m^-2, 51.7% "
      "above withdrawal and 69.5% above the no-bat case; the natural bat population alone "
      "contributes 11.7%. Channel ablation attributes +159.9 kg ha^-1 to insectivory, +329.0 to "
      "pollination, -311.5 to predation by raptors, and +153.5 to interactions.")

    P("A 150-plan Latin-hypercube search was screened on four objectives: profit, stability, "
      "biodiversity and yield. Thirty-one plans are non-dominated. The knee point uses herbicide "
      "intensity 0.87, mechanical weeding 0.84, bat houses and an organic area share of 0.12, and "
      "returns 9744 CNY ha^-1 profit with 5308 kg ha^-1 seed, pest biomass 0.085 g C m^-2, soil "
      "carbon 1739 g C m^-2 and input costs of 872 CNY ha^-1. Biodiversity is the cost of that "
      "position: the knee point carries the lowest Shannon index of the 150 plans, while the "
      "low-profit end of the front gives up about a third of the yield for the highest diversity. "
      "The plan the letter recommends is a low-input point on the same front: it spends 305 CNY "
      "ha^-1 on inputs and returns 8620 CNY ha^-1 with 4462 kg ha^-1 of seed. Sensitivity "
      "runs show that crop carrying capacity is the strongest parameter, moving yield by -20.2% and "
      "+29.3% under a 20% change. The practical message is an ordering: replace a function before "
      "removing the input that performs it.")
    PAGEBREAK()

    # ================= TOC =================
    H1("Table of Contents")
    add_toc(PAGES_MAP)
    PAGEBREAK()

    # ================= 1 Introduction =================
    H1("1. Introduction")
    P("A cleared forest does not become a stable farm overnight. Crop fields are colonized by weeds "
      "and pests, natural enemies follow their prey, edge habitats mature, and native species "
      "return. At the same time farmers spray, fertilize, mow and harvest. The state of the system "
      "at the end of a season therefore depends on both ecological succession and management, and "
      "its stability cannot be judged from a single growing season. This is the practical difficulty "
      "the problem describes, and it is also the modelling difficulty: a static food web cannot "
      "represent a system that is still assembling.")

    P("The 2025 ICM Problem E asks for a model that tracks this forest-to-farm transition, includes "
      "natural processes and human decisions, and answers four linked questions. The first concerns "
      "the initial agricultural food web under seasonal forcing and chemical use. The second "
      "concerns edge-habitat maturation and the return of native species. The third asks whether "
      "removing herbicide and adding bats can restore balance, and compares another beneficial "
      "species. The fourth examines components of organic farming and their effects on pest control, "
      "crop health, plant reproduction, biodiversity, long-term sustainability and cost. A one-page "
      "letter to a farmer must translate the results into practice.")

    P("We answer these questions with one model instead of four. A shared seasonally forced food web "
      "is extended with earthworms and raptors for the second question, with bats, parasitoids and "
      "explicit channel ablations for the third, and with a seven-dimensional management vector for "
      "the fourth. The equations, parameters and stability definitions stay fixed across scenarios. "
      "This choice costs some flexibility. A model built for one question rarely fits another "
      "perfectly. In exchange it buys comparability: a difference between two scenarios can be "
      "traced to a management decision or to a species.")

    P("Three design decisions distinguish the model from a textbook food web. First, the "
      "agricultural cycle is represented as events inside a periodically forced system, and "
      "stability is analysed with Floquet multipliers instead of a fixed-point Jacobian. That avoids "
      "the artificial neutral direction created by slow habitat variables. Second, chemicals are "
      "state variables with degradation kinetics, so withdrawing a chemical is a gradual process "
      "with legacy effects. Third, the bat effect is decomposed into insectivory, pollination, "
      "predation and interaction channels by explicit ablations, and we report that these channels "
      "are not additive.")

    P("Our approach draws on several literatures. Exclusion experiments show that bats and birds "
      "raise yield in agroforestry [1, 2], and bat pest consumption has been quantified in orchards "
      "[13]. Periodically forced consumer-resource systems require Floquet-type stability analysis "
      "[3]. Sublethal pesticide effects and non-target impacts motivate the dose-response "
      "formulation [4, 12]. Nocturnal pollination and its vulnerability are documented in [5, 6]. "
      "Organic systems have been compared with conventional ones in meta-analyses [7]. "
      "Vegetation-management studies in vineyards link management intensity to biodiversity and "
      "ecosystem services [8], and habitat-management studies show that field margins and vegetation structure drive natural "
      "enemies [9, 10]. Integrated weed management provides the basis for the herbicide-reduction "
      "scenarios [11], and pesticide degradation data inform the residue model [14].")

    # ================= 2 Assumptions =================
    H1("2. Assumptions and Notation")
    P("The model rests on three structural assumptions. The study unit is one hectare of field plus "
      "an adjacent edge strip, and the regional species pool acts as a constant source whose inflow "
      "is modulated by edge maturity. Consumption follows Holling type II responses, with a "
      "multi-prey disc equation for generalist predators. Chemical effects act through residue "
      "concentration and dose response, and resistance evolution is not modelled within the "
      "analysed horizon.")

    P("Five further assumptions are relaxable. Temperature is the main seasonal driver and rainfall "
      "enters as interannual noise. Farmer decisions are exogenous scenarios except in the fourth "
      "question. Spatial heterogeneity is aggregated into an edge-area share and colonization "
      "fluxes. Regional bat and bird populations are constant sources. Prices, costs and the organic "
      "premium are constant within a scenario. Each of these is discussed qualitatively instead "
      "of being given its own state.")

    P("Table 1 lists the symbols used throughout. All biomass and litter states are expressed in "
      "grams of carbon per square metre, nitrogen in grams of nitrogen per square metre, and "
      "residues in milligrams of active ingredient per kilogram of soil. Vertebrate abundances are "
      "converted to biomass equivalents before entering the equations, so no equation mixes "
      "individuals with biomass.")

    TABLE([
        ["Symbol", "Meaning", "Unit"],
        ["C, W, V", "crop, weed, edge vegetation biomass", "g C m^-2"],
        ["S_N, L", "soil available nitrogen, litter stock", "g N m^-2, g C m^-2"],
        ["H, A", "pest and predatory arthropod biomass", "g C m^-2"],
        ["P, B, R", "pollinator, bat, insectivorous bird biomass", "g C m^-2"],
        ["Q, D, O", "parasitoid, earthworm, raptor biomass", "g C m^-2"],
        ["X_H, X_P", "herbicide and insecticide residue", "mg a.i. kg^-1"],
        ["E, SOM", "edge maturity, soil organic carbon", "-, g C m^-2"],
        ["u_H, u_P, u_M, u_org, u_B", "normalized intensities of the management decisions", "dimensionless"],
        ["rho_f, rho_y", "Floquet and annual-map spectral radii", "-"],
        ["lambda_poll", "fruit-set factor from pollinators", "-"],
    ], "Table 1. Main symbols.")

    # ================= 3 Model =================
    H1("3. Model Formulation")
    H2("3.1 Two timescales")
    P("The system has a fast timescale and a slow one. Fast variables are integrated continuously "
      "within a year, with a period of 365 days. Edge maturity and soil organic carbon are updated "
      "at year boundaries. This separation allows the model to distinguish seasonal variability "
      "from long-term degradation, and it defines the stability objects used later. A single "
      "twenty-year integration would mix the two, and a seasonal average would hide the mechanism "
      "that drives pest outbreaks. Figure 1 lays out the workflow. Inputs and assumptions feed a core food-web model, four "
      "scenario families are generated, numerical solvers produce trajectories and stability "
      "metrics, and the results pass a validation stage before they are reported. The four scenario "
      "families share the same core, so the figure shows one model box and four branches.")

    FIGURE("flow_overall_model.png", "Figure 1. Model workflow. Boxes denote model components, "
                                     "scenarios and outputs, and arrows denote data and control flow.", 14.0)

    H2("3.2 Seasonal forcing and the agricultural cycle")
    P("Temperature follows a cosine annual cycle and enters growth through a Gaussian response. The crop is an annual, partially pollinator-dependent oilseed crop such as rapeseed. Crop "
      "activity is gated by planting and harvest windows, flowering is gated separately, and insect "
      "activity and vertebrate residency are gated by logistic windows. Planting, fertilization, "
      "spraying and mowing enter as short pulses. The agricultural cycle therefore appears "
      "explicitly: the crop starts from a seed pulse, grows through a gated window, loses biomass to "
      "herbivores, and is removed at harvest. The temperature curve in Figure 2 peaks near day 200, while the crop window opens near "
      "day 100 and closes near day 280. The crop therefore experiences rising and falling "
      "temperatures within one season.")

    P("The right panel of Figure 2 gives the two residues. Herbicide is applied early, when the crop "
      "is small and weeds are establishing, and insecticide is applied later, when pest populations "
      "have built up. Both residues decay exponentially, with half-lives of 20 and 8 days. The "
      "asymmetry is deliberate: herbicide has a longer tail because soil degradation is slower, "
      "which is also why withdrawal in the third question is modelled as a ramp, "
      "which lets the residue decay.")

    FIGURE("raw_q1_forcing.png", "Figure 2. Seasonal forcing. The left panel shows temperature and "
                                  "the three phenology gates. The right panel gives herbicide and "
                                  "insecticide residues after application.", 14.0)

    H2("3.3 Feeding fluxes and functional responses")
    P("All consumers are written in flux form. The per-unit-biomass consumption rate of predator j on "
      "prey i is given by Equation (1), where a is the attack rate and h is the handling time. The "
      "product a h X is dimensionless, so the handling time carries units of days. Total "
      "flux from prey to predator is the product of predator biomass and this rate, and the same "
      "flux appears with opposite signs in the two equations. Writing the system this way avoids the "
      "common error of placing a biomass flux inside a per-capita bracket.")

    EQ(r"g_{ji}(X_i)=\frac{a_{ji}X_i}{1+a_{ji}h_{ji}X_i}", 1)
    P("For generalist predators that eat several prey, the disc equation is used with a shared "
      "denominator. The shared handling time matters: adding three separate Holling responses "
      "double-counts the time a predator spends handling food. In the bird equation, for example, "
      "the intake rate is written as a single disc expression with three prey terms in the numerator "
      "and three handling terms in the denominator. This is a small technical point with a visible "
      "consequence, because it changes how strongly birds can suppress pests when alternative prey "
      "are abundant.")

    H2("3.4 The full dynamical system")
    P("The complete system is listed below so that every state and every flux can be checked. "
      "Equations (2) and (3) describe the two cultivated producers, Equation (4) the edge "
      "vegetation, and Equations (5) and (6) the litter and nitrogen pools. Equations (7) to (11) "
      "cover the pest, the predatory arthropod, the pollinator, the bat and the bird. Equations (12) "
      "to (14) cover the three species that appear only in later questions: the parasitoid, the "
      "earthworm and the raptor. Equations (15) and (16) describe chemical fate, and Equation (17) "
      "converts pollination into yield.")

    EQ(r"\frac{dC}{dt}=C\left[r_Cf_Nf_T\sigma_C\left(1-\frac{C+\beta_{CW}W}{K_C}\right)-m_C-\phi_C\frac{X_H}{X_H+H_{50,C}}\right]-Hg_{HC}(C)+\iota_C(t)-\eta(t)C", 2)
    EQ(r"\frac{dW}{dt}=W\left[r_Wf_Nf_T\left(1-\frac{W+\beta_{WC}C}{K_W}\right)-m_W-\phi_W\frac{X_H}{X_H+H_{50,W}}-\gamma_{mow}(t)\right]-Hg_{HW}(W)+g_{seed}\left(1-\frac{W}{K_W}\right)", 3)
    EQ(r"\frac{dV}{dt}=V\left[r_Vf_T\left(1-\frac{V}{K_V}\right)-m_V-\gamma_{mow}(t)\right]+c_VE\left(1-\frac{V}{K_V}\right)", 4)
    EQ(r"\frac{dL}{dt}=(1-\epsilon_L)I_{lit}-\kappa_{lit}L-Dg_{DL}(L)", 5)
    EQ(r"\frac{dS_N}{dt}=F_{fert}(t)+\frac{\kappa_{lit}}{\phi_{CN}}L+\kappa_DD+\frac{\kappa_wDg_{DL}(L)}{\phi_{CN}}-U_N-l_SS_N", 6)
    EQ(r"\frac{dH}{dt}=H\left[f_{act}(e_Hg_{HC}+e_{HW}g_{HW})\left(1-\frac{H}{K_H}\right)-m_H-\phi_H\frac{X_P}{X_P+H_{50,H}}\right]-Ag_{AH}-Bg_{BH}-Rg_{RH}-Qg_{QH}+c_HE\left(1-\frac{H}{K_H}\right)", 7)
    EQ(r"\frac{dA}{dt}=A\left[e_Af_{act}g_{AH}(H)\left(1-\frac{A}{K_A}\right)-m_A-\phi_A\frac{X_P}{X_P+H_{50,A}}\right]-Rg_{RA}+c_AE\left(1-\frac{A}{K_A}\right)", 8)
    EQ(r"\frac{dP}{dt}=P\left[e_Pf_{act}(\psi_CC_{fl}+\psi_VV)\left(1-\frac{P}{K_P}\right)-m_P-\phi_P\frac{X_P}{X_P+H_{50,P}}\right]-Rg_{RP}+c_PE\left(1-\frac{P}{K_P}\right)", 9)
    EQ(r"\frac{dB}{dt}=B\left[e_Bf_B(g_{BH}+\psi_BC_{fl})\left(1-\frac{B}{K_B}\right)-m_B-\phi_B\frac{X_P}{X_P+H_{50,B}}\right]-Og_{OB}+c_BE\left(1-\frac{B}{K_B}\right)+u_B\iota_B(t)", 10)
    EQ(r"\frac{dR}{dt}=R\left[e_Rf_B\,\Pi_R\left(1-\frac{R}{K_R}\right)-m_R-\phi_R\frac{X_P}{X_P+H_{50,R}}\right]-Og_{OR}+c_RE\left(1-\frac{R}{K_R}\right)", 11)
    EQ(r"\frac{dQ}{dt}=Q\left[e_Qf_{act}g_{QH}(H)\left(1-\frac{Q}{K_Q}\right)-m_Q-\phi_Q\frac{X_P}{X_P+H_{50,Q}}\right]+c_QE\left(1-\frac{Q}{K_Q}\right)+\iota_Q(t)", 12)
    EQ(r"\frac{dD}{dt}=D\left[e_Df_{act}g_{DL}(L)\left(1-\frac{D}{K_D}\right)-m_D-\phi_D\frac{X_P}{X_P+H_{50,D}}\right]+c_DE\left(1-\frac{D}{K_D}\right)", 13)
    EQ(r"\frac{dO}{dt}=O\left[e_O\,\Pi_O\left(1-\frac{O}{K_O}\right)-m_O-\phi_O\frac{X_P}{X_P+H_{50,O}}\right]+c_OE\left(1-\frac{O}{K_O}\right)", 14)
    EQ(r"\frac{dX_H}{dt}=\frac{10^6}{M_{soil}}U_H(t)-\frac{\ln 2}{DT_{50,H}}X_H", 15)
    EQ(r"\frac{dX_P}{dt}=\frac{10^6}{M_{soil}}U_P(t)-\frac{\ln 2}{DT_{50,P}}X_P", 16)
    EQ(r"\lambda_{poll}=\lambda_0+(1-\lambda_0)\min\left(1,\frac{P+\omega_B\nu_BB}{P_{ref}}\right),\qquad Y=\lambda_{poll}\int_{t_h}^{t_h+\Delta_h}\eta C\,dt", 17)

    P("Four composite terms keep the display compact. H_W is the herbicide mortality of weeds and S_W is the seed-bank supply. U_N is the nitrogen uptake, written with the "
      "same f_N and density factors as growth so that a nitrogen-limited plant neither grows nor "
      "absorbs. Pi_R and Pi_O are the multi-prey disc expressions for birds and raptors, each with a "
      "shared handling-time denominator. The litter input I_lit collects the mortality fluxes of all "
      "functional groups, and it is split into an immediately humified fraction and a decomposable "
      "stock.")

    H2("3.5 Chemical fate")
    P("Chemicals are state variables with first-order degradation, as in Equations (15) and (16). "
      "Spraying raises the residue, degradation lowers it, and the residue drives mortality of "
      "target and non-target species through a half-effect concentration. Withdrawal is therefore a "
      "ramp followed by a decay tail, and the tail explains why the effect of a spray outlives the "
      "spray itself.")

    H2("3.6 Stability metrics")
    P("Because the system is periodically forced, we do not linearize around a fixed point. The fast "
      "subsystem is integrated to a fixed point of the one-year map, and its monodromy matrix gives "
      "Floquet multipliers. The spectral radius rho_f below one implies a stable seasonal cycle, and "
      "the recovery time is minus one over Lambda, with Lambda equal to the logarithm of rho_f "
      "divided by 365. A second measure, the annual-map spectral radius rho_y, includes edge "
      "maturity and soil carbon. During maturation, when no periodic orbit exists, we report the "
      "year-by-year finite-time contraction rate instead of forcing a Floquet interpretation. The distinction matters. A naive analysis that linearizes at the seasonal mean reports one "
      "number and hides phase-dependent amplification. The Floquet spectrum shows which perturbations grow within a season and which decay across "
      "years. It is also why the cycle can be stable even though pest biomass varies by a factor of "
      "about seven within a year.")

    H2("3.7 Parameterization")
    P("Parameters are taken from published ranges where available and calibrated otherwise. Table 2 "
      "reports the values that most strongly affect the conclusions. Ranges marked provisional are "
      "modelling-stage magnitude judgements, not literature values, and Section 8 discusses their "
      "influence. Two "
      "entries deserve comment. The bat attack rate sits at the upper end of the functional-response "
      "range because bats forage over a large area relative to their biomass. The equivalent "
      "pollinator efficiency is expressed in pollinator units per unit bat biomass, so its value is large in absolute terms.")

    TABLE([
        ["Parameter", "Value", "Unit", "Source type"],
        ["Crop growth rate r_C", "0.09", "d^-1", "physiological range"],
        ["Crop carrying capacity K_C", "600", "g C m^-2", "yield constraint"],
        ["Weed growth rate r_W", "0.08", "d^-1", "literature order"],
        ["Pest attack rate a_HC", "0.004", "m^2 gC^-1 d^-1", "functional-response range"],
        ["Bat attack rate a_BH", "4.0", "m^2 gC^-1 d^-1", "upper end, calibrated"],
        ["Bat pollination efficiency nu_B", "50", "-", "equivalent pollinator units"],
        ["Nitrogen half-saturation K_N", "1.0", "g N m^-2", "literature order"],
        ["Litter decay kappa_lit", "0.012", "d^-1", "decomposition range"],
        ["Herbicide half-life DT50_H", "20", "d", "registration data"],
        ["Insecticide half-life DT50_P", "8", "d", "registration data"],
        ["Harvest rate eta", "0.30", "d^-1", "field practice"],
        ["Harvest index H_I", "0.50", "-", "crop science"],
    ], "Table 2. Key parameters. Provisional entries are discussed in Section 8.")

    # ================= 4 Q1 =================
    H1("4. Question 1: Chemical Stress and Seasonality")
    H2("4.1 Design of the chemical grid")
    P("We ran a five-by-five grid of herbicide and insecticide intensities over six years. The grid "
      "contains the four corners in which each chemical is either absent or applied at full "
      "intensity, and a centre point at half intensity for both. Each run started from the same "
      "initial state and used the same weather, so a difference between two cells comes from the "
      "chemical inputs alone.")

    PS("The grid is deliberately coarse. Its purpose is to expose the shape of the response surface, "
       "not to locate an optimum.")

    H2("4.2 Seasonal trajectories")
    P("Figure 3 traces the baseline two-year trajectory. Crop biomass rises through the growth window "
      "and peaks near 574 g C m^-2, then falls sharply at harvest. Pest biomass follows with a lag of "
      "several weeks, which is visible in the middle panel as a peak that arrives after the crop peak "
      "and again after the second planting. Predatory arthropods track the pest peak but remain an "
      "order of magnitude smaller in biomass. The right panel shows bats, scaled by a factor of one hundred, and "
      "pollinators at their unscaled values, both of which oscillate with the season and never "
      "approach their carrying capacities. The panels share a phase structure: the crop "
      "leads, the pest follows, and the predator follows the pest. That ordering is the reason a "
      "single sample date can give opposite impressions of the same field, and it is why the model "
      "keeps daily resolution instead of reporting seasonal means.")

    FIGURE("process_q1_timeseries.png", "Figure 3. Baseline two-year trajectories. Left: crop and "
                                        "weeds. Middle: pests and predatory arthropods. Right: bats "
                                        "(scaled by 100) and pollinators.", 14.0)

    P("Nothing in this system sits at equilibrium. Crop biomass is zero before planting, pest biomass "
      "collapses in winter, and the predator community lags both.")

    H2("4.3 Yield and pest response")
    P("The left panel of Figure 4 gives seed yield and the right panel gives mean pest biomass. "
      "In the lower-left corner, where neither chemical is applied, yield is 3506 kg ha^-1 and "
      "pest biomass is 3.07 g C m^-2. Moving right along the bottom row, herbicide reduces weeds "
      "from 12.12 to 8.94 g C m^-2 but leaves pests near 3 g C m^-2, and yield falls slightly to "
      "3441 kg ha^-1. Moving up the left column, insecticide reduces pests to 2.18 g C m^-2 and "
      "predators to 0.46 g C m^-2, and yield falls to 3424 kg ha^-1. The upper-right corner "
      "combines both effects: pests fall to 1.98 g C m^-2, predators to 0.42, and yield reaches "
      "3688 kg ha^-1.")

    FIGURE("result_q1_gradient.png", "Figure 4. Seed yield (left) and mean pest biomass (right) "
                                      "across the herbicide-insecticide grid. Numbers inside the "
                                      "cells are the simulated values.", 13.5)

    P("Yield is only half of the response. Table 3 adds the pest coefficient of variation. "
      "Insecticide does most of the damage to stability: the coefficient rises from 1.90 without "
      "inputs to 2.42 with insecticide alone and 2.46 at full treatment, while predator biomass "
      "falls from 0.66 to 0.46 g C m^-2 under insecticide alone and to 0.42 at full treatment. "
      "Spraying removes the predators that would damp the pest "
      "cycle, so each application buys a lower mean pest biomass at the price of a larger swing. "
      "Yield along that path falls from 3506 to 3424 kg ha^-1, because the same sprays reach the "
      "pollinators and the fruit-set factor slips from 0.984 to 0.977. The trade-off behind the "
      "advice in the letter is therefore narrow. Reducing insecticide raises yield only where the "
      "predator and pollinator functions are replaced, by bats, by flowering margins or by released "
      "natural enemies; without that replacement the field keeps the pest cycle the sprays created.")

    TABLE([
        ["Chemical input", "", "", "Ecosystem response", "", "", "", "Economics", ""],
        ["Scenario", "u_H", "u_P", "Weed", "Pest", "Predator", "Pest CV", "Yield", "Change"],
        ["None", "0.00", "0.00", "12.12", "3.07", "0.66", "1.90", "3506", "-"],
        ["Insecticide", "0.00", "1.00", "13.39", "2.18", "0.46", "2.42", "3424", "-2.3%"],
        ["Herbicide", "1.00", "0.00", "8.94", "2.93", "0.64", "1.97", "3441", "-1.9%"],
        ["Half dose", "0.50", "0.50", "10.63", "2.58", "0.56", "2.20", "3232", "-7.8%"],
        ["Full", "1.00", "1.00", "9.60", "1.98", "0.42", "2.46", "3688", "+5.2%"],
    ], "Table 3. Corner and centre scenarios of the chemical grid, with six-year means. Weed, pest "
       "and predator in g C m^-2; yield in kg ha^-1.", merges=[(0, 0, 2), (0, 3, 6), (0, 7, 8)])
    H2("4.4 Stability of the seasonal cycle")
    P("Figure 5 reports the Floquet radius and the recovery time for the three reference scenarios. "
      "All three are stable, with radii between 0.57 and 0.58 and recovery times between 658 and 661 "
      "days. The differences are small, which is itself informative: the cycle remains stable under "
      "all three chemical regimes, so the risk is not a collapse of the cycle. It is a change in its composition and in the "
      "time it takes to recover from a shock.")

    FIGURE("result_q1_stability.png", "Figure 5. Floquet spectral radius and recovery time for the "
                                       "three reference scenarios.", 9.0)

    # ================= 5 Q2 =================
    H1("5. Question 2: Edge Maturation and Species Return")
    H2("5.1 Two returning species")
    P("Edge maturity rises logistically from 0.20 toward its fixed point and drives the colonization "
      "of native species. We introduce two species with distinct roles. Earthworms are decomposers "
      "that accelerate nitrogen turnover. Raptors are top predators that feed on birds, bats and rodents. "
      "Neither is present in the first question, so their effects are measured against a common "
      "baseline. The Q2 baseline is a 20-year mean with E starting at 0.20 and both species absent, which is why its yield (3462 kg ha^-1) differs from the Q1 and Q3 baselines. Figure 6 traces the maturation: edge maturity approaches 0.71 by year twenty, "
      "earthworm biomass stabilizes near 9.1 g C m^-2, and raptor biomass rises more slowly because "
      "its prey base develops later.")

    PS("Colonization is slow at the start. With E at 0.20, the inflow of both species is small, and "
       "the first three years look much like the baseline.")

    FIGURE("raw_q2_returning_species.png", "Figure 6. Edge-habitat maturation and the return of "
                                           "earthworms and raptors over twenty years.", 14.0)

    H2("5.2 Production and stability trade-off")
    P("Earthworms raised yield from 3462 to 3498 kg ha^-1, a gain of 1.05%, by accelerating "
      "nitrogen turnover. The predator community changed little (0.491 to 0.480 g C m^-2), and "
      "pest biomass fell slightly from 2.14 to 2.08 g C m^-2. Figure 7 compares the four variants. Raptors lowered yield to 3277 "
      "kg ha^-1, a loss of 5.3%, because raptor predation reduces bat biomass from 0.018 to 0.014 "
      "and releases pests to 2.80 g C m^-2. Introducing both species gave 3146 kg ha^-1, which is "
      "worse than raptors alone: once raptors are present, adding earthworms does not recover the "
      "loss. The interaction is negative, and a policy that promotes both without distinguishing "
      "them would report a net loss.")

    FIGURE("result_q2_species_effects.png", "Figure 7. Yield, pest pressure and soil carbon under "
                                            "four species-return scenarios. Soil-carbon bars are "
                                            "annotated and the axis is truncated to show differences.", 14.0)

    TABLE([
        ["Scenario", "Yield (kg ha^-1)", "Yield change", "Pest (g C m^-2)", "Soil C (g C m^-2)",
         "rho_f", "TR (d)"],
        ["No returning species", "3462", "-", "2.14", "1679", "0.576", "662"],
        ["Earthworm only", "3498", "+1.05%", "2.08", "1694", "0.559", "629"],
        ["Raptor only", "3277", "-5.3%", "2.80", "1687", "0.573", "656"],
        ["Both", "3146", "-9.1%", "2.71", "1697", "0.510", "542"],
    ], "Table 4. Species-return scenarios, with final-year soil organic carbon and seasonal-cycle "
       "stability.")

    P("Table 4 reports the four variants side by side.")

    H2("5.3 Stability after species return")
    P("Species return does not destabilize the seasonal cycle. The four variants keep Floquet "
      "radii between 0.510 and 0.576, and the mixed community recovers fastest: the return time "
      "falls from 662 to 542 days when both species are present. Figure 8 gives the ordering. The "
      "single-species gain comes from the decomposer pathway. The earthworm-only case shortens "
      "recovery to 629 days, while the raptor-only case reaches 656, so faster nitrogen turnover "
      "does more for recovery than pest removal by a top predator. Raptors act on the pest side and "
      "shorten recovery only slightly, because they also remove bats from the same prey base. The "
      "two pathways are complementary: together they reach 542 days, shorter than either alone.")

    FIGURE("result_q2_stability.png", "Figure 8. Floquet spectral radius and recovery time for the "
                                       "four species-return scenarios.", 12.0)
    # ================= 6 Q3 =================
    H1("6. Question 3: Herbicide Withdrawal, Bats and Alternatives")
    H2("6.1 The withdrawal experiment")
    P("We ramp herbicide intensity to zero over one year starting in year 3, leaving the residue "
      "to decay, and compare five management scenarios. Figure 9 gives the schedule and the weed "
      "response. Weeds spike in the first season after withdrawal, then settle at a higher level "
      "than in the conventional case. Figure 10 follows the producers and consumers around the "
      "transition, with the dotted line marking year 3. The crop cycle continues without a regime "
      "shift, which is the first sign that withdrawal is survivable. The Q3 baseline is a 10-year mean with the raptor present and the earthworm biomass fixed at 8.0 g C m^-2, so its yield (3104 kg ha^-1) is lower than the Q2 baseline.")

    FIGURE("raw_q3_withdrawal_schedule.png", "Figure 9. Herbicide withdrawal schedule and weed "
                                             "biomass response.", 14.0)
    P("The transition does not restart the system. The next figure follows the same years at daily "
      "resolution, and the dotted line marks the first day of withdrawal.")

    FIGURE("process_q3_withdrawal.png", "Figure 10. Producers and consumers before and after "
                                        "herbicide withdrawal. The dotted line marks year 3.", 14.0)
    H2("6.2 The bat counterfactual")
    P("Withdrawal raised weed biomass from 8.01 to 9.63 g C m^-2, and yield stayed near 3153 "
      "kg ha^-1 against 3104 kg ha^-1 in the conventional scenario. The crop compensated for part "
      "of the weed pressure, so the yield penalty is small. The bat counterfactual is much larger. "
      "When bats are removed entirely, pest biomass rises from 2.79 to 3.60 g C m^-2, the "
      "fruit-set factor falls from 0.978 to 0.871, and yield drops to 2822 kg ha^-1.")

    P("Bat houses change the picture in the other direction. Raising the carrying capacity and "
      "colonization flux by half lets the local population grow from 0.013 to 0.020 g C m^-2. Pest "
      "biomass falls to 1.17 g C m^-2, the fruit-set factor reaches 0.995, and yield rises to 4783 "
      "kg ha^-1, which is 51.7% above the withdrawal case. Measured against no bats, the bat-house "
      "effect is +69.5%; the natural bat population alone accounts for +11.7%.")

    P("The size of that response depends on how far the roost capacity is raised. Figure 11 sweeps "
      "the multiplier from 1.0 to 2.0 around the bat-house setting. Yield climbs from 3153 to 5330 "
      "kg ha^-1, pest biomass falls from 2.79 to 0.04 g C m^-2, and the predatory arthropods that "
      "share the pest prey fall from 0.58 to 0.02 g C m^-2. Most of the change is compressed "
      "between 1.2 and 1.7, where yield rises by 1985 kg ha^-1. The 1.5 setting used in Table 5 "
      "sits inside that steep segment, so the +51.7% is a threshold effect and not a linear return "
      "on roost capacity. Beyond 1.7 the curve saturates: the last three steps add 55 kg ha^-1 of "
      "yield and almost no bat biomass. The predator decline is the second-order part of the same "
      "effect. Once the bats remove the pest, the predatory arthropods lose their food base, which "
      "is the food limitation seen from the other side in the no-bat ablation.")

    FIGURE("result_q3_bat_dose.png", "Figure 11. Bat-house intensity sweep. Top: yield against the "
                                     "bat capacity and colonization multiplier. Bottom: bat and "
                                     "pest biomass on a log scale, with the 1.5 setting marked by "
                                     "the dashed line.", 12.0)

    P("Parasitoid release reaches 3412 kg ha^-1. The scenario assumes integrated management with "
      "insecticide at 30% of the conventional dose, because a full dose removes the released "
      "parasitoids before they establish. The two species are not interchangeable: parasitoids "
      "suppress pests but do not pollinate, while bats do both. Figure 12 places the five scenarios "
      "side by side; the no-bat case sits at about 0.91 of the conventional yield and 1.33 times "
      "its pest biomass.")

    FIGURE("result_q3_alternatives.png", "Figure 12. Five management scenarios relative to the "
                                          "conventional case. Left: yield and pests. Right: pest "
                                          "variability, with the dotted line marking the "
                                          "conventional value.", 14.0)

    TABLE([
        ["Scenario", "Bat (g C m^-2)", "Pest (g C m^-2)", "Predator (g C m^-2)",
         "Fruit set", "Yield (kg ha^-1)"],
        ["Conventional", "0.013", "2.71", "0.569", "0.977", "3104"],
        ["Herbicide removal", "0.013", "2.79", "0.585", "0.978", "3153"],
        ["Removal, no bats", "0.000", "3.60", "0.772", "0.871", "2822"],
        ["Removal + bat houses", "0.020", "1.17", "0.146", "0.995", "4783"],
        ["Removal + parasitoid", "0.013", "3.16", "0.693", "0.983", "3412"],
    ], "Table 5. Management scenarios for herbicide withdrawal, with ten-year means.")
    P("Table 5 lists the five scenarios. The bat-house row is the only one that raises yield "
      "above the withdrawal baseline.")
    H2("6.3 Channel ablation")
    P("To separate the bat channels we disabled one function at a time while keeping bats "
      "present: insectivory, pollination and predation by raptors. Figure 13 breaks down the "
      "result. Removing insectivory raises pest biomass to 3.60 g C m^-2 and lowers yield to 2993 "
      "kg ha^-1. Removing pollination lowers the fruit-set factor to 0.877 and yield to 2824 "
      "kg ha^-1. Removing raptor predation has the opposite sign: bats become more abundant, pest "
      "biomass falls to 2.14 g C m^-2, and yield rises to 3464 kg ha^-1.")

    FIGURE("result_q3_ablation.png", "Figure 13. Channel ablations. Pest suppression, pollination "
                                      "and yield when one bat function is disabled.", 14.0)

    P("The channel effects are not additive, and the arithmetic shows why a simple sum would "
      "mislead. Relative to herbicide removal at 3153 kg ha^-1, insectivory contributes +159.9, "
      "pollination +329.0, and predation by raptors -311.5 kg ha^-1. The three terms sum to +177.4, "
      "and the remaining +153.5 is an interaction term. The total bat effect, measured against no "
      "bats, is +330.9 kg ha^-1. We report the decomposition as an attribution of the total effect, "
      "because the system re-equilibrates after each ablation and the indirect response is part "
      "of what the ablation measures. The negative predation term deserves attention. Raptors eat "
      "bats, so protecting raptors reduces the pest-control service that bats provide.")

    TABLE([
        ["Scenario", "Bat (g C m^-2)", "Pest (g C m^-2)", "Predator (g C m^-2)",
         "Fruit set", "Yield (kg ha^-1)"],
        ["Full bats", "0.013", "2.79", "0.585", "0.978", "3153"],
        ["No bats", "0.000", "3.60", "0.772", "0.871", "2822"],
        ["No insectivory", "0.007", "3.60", "0.772", "0.924", "2993"],
        ["No pollination", "0.013", "2.81", "0.587", "0.877", "2824"],
        ["No predation", "0.017", "2.14", "0.467", "0.979", "3464"],
    ], "Table 6. Channel ablations. Each row disables one function while bats remain present.")
    P("Table 6 reports the same ablations as numbers.")
    H2("6.4 Alternative species")
    P("Three conclusions follow. Bat houses are the only intervention that restores production: "
      "they raise yield from 3153 to 4783 kg ha^-1, a gain of 51.7%, and cut pest biomass from "
      "2.79 to 1.17 g C m^-2. A parasitoid release under integrated management reaches 3412 "
      "kg ha^-1, which is better than withdrawal alone but well below the bat-house case. Protecting "
      "raptors has a hidden cost, because raptors eat bats, and the predation channel is negative "
      "for production even though it is positive for the raptor population.")
    # ================= 7 Q4 =================
    H1("7. Question 4: Organic Portfolios")
    H2("7.1 Decision space and objectives")
    P("We search a seven-dimensional management space: herbicide and insecticide intensity, organic "
      "fertilizer share, mechanical weeding, edge-area share, bat-house investment and organic area "
      "share. The 150 plans are drawn by Latin-hypercube sampling over that box, each is simulated "
      "for five years, and the objective vectors are screened for Pareto dominance on four "
      "objectives: profit, stability, biodiversity (Shannon) and yield. Figure 14 displays the "
      "sampled decisions, with marker size proportional to profit and colour marking the organic "
      "area share. The samples spread across the full range of herbicide and insecticide "
      "intensities, which is what Latin-hypercube sampling is meant to achieve.")

    FIGURE("raw_q4_decision_space.png", "Figure 14. Sampled decision space. Marker size is "
                                         "proportional to profit and colour marks the organic area "
                                         "share.", 9.5)

    H2("7.2 Pareto front and knee point")
    P("Figure 15 plots the profit-yield plane for the 150 samples. Thirty-one plans are "
      "non-dominated on all four objectives, and Table 7 lists five representative points. The knee "
      "point, marked with an open circle, is the Pareto point furthest from the chord between the "
      "two profit extremes. It uses herbicide intensity 0.87, insecticide 0.94, a fertiliser share "
      "of 0.82, mechanical weeding 0.84, an edge share of 0.08, bat houses and an organic area "
      "share of 0.12. It returns 9744 CNY ha^-1 profit and 5308 kg ha^-1 seed, with pest biomass "
      "0.085 g C m^-2, crop biomass 255.8 g C m^-2, a fruit-set factor of 1.000, soil carbon 1739 "
      "g C m^-2, stability 0.363 and Shannon diversity 0.745. The organic share of 0.12 leaves 88% "
      "of the area under conventional management, where herbicide is applied at u_H=0.87; the "
      "effective intensity is (1-u_org)u_H=0.76.")

    FIGURE("result_q4_pareto.png", "Figure 15. Profit-yield Pareto front and the knee-point plan.", 14.0)

    TABLE([
        ["Plan", "u_H", "u_M", "u_org", "u_B", "Profit", "Stability",
         "Shannon", "Yield", "Pest", "Soil C", "Cost"],
        ["S13", "0.03", "0.43", "0.14", "1", "10026", "0.338", "0.777", "5275", "0.157", "1791", "524"],
        ["S145", "0.87", "0.84", "0.12", "1", "9744", "0.363", "0.745", "5308", "0.085", "1739", "872"],
        ["S22", "0.55", "0.04", "0.97", "1", "8599", "0.290", "0.847", "4464", "1.368", "1856", "330"],
        ["S143", "0.93", "0.05", "0.98", "0", "7000", "0.344", "0.876", "3563", "3.069", "1844", "126"],
        ["S77", "0.08", "0.95", "0.91", "0", "6756", "0.345", "0.867", "3547", "3.070", "1733", "338"],
    ], "Table 7. Representative Pareto-optimal plans, labelled by sample. Profit and cost in CNY "
       "ha^-1, yield in kg ha^-1, pest biomass and soil carbon in g C m^-2. Stability is the "
       "spectral-radius proxy and Shannon is the biodiversity index. The full set of 31 points is "
       "in the result file. S145 is the knee point and S77 is the low-profit plan A.")
    P("Table 7 shows why a single recommendation would mislead. The highest-profit plan earns 282 "
      "CNY ha^-1 more than the knee point and spends 348 CNY ha^-1 less on inputs, but it carries "
      "nearly twice the pest biomass and 33 kg ha^-1 less seed. The two low-profit plans at the "
      "bottom earn about 7000 CNY ha^-1 at 126 to 338 CNY ha^-1 of input cost, against 872 at the "
      "knee, and they hold the highest diversity on the front; their yield is about 3560 kg ha^-1, "
      "two thirds of the knee-point value, because neither installs bat houses. Plan S77 remains "
      "non-dominated for a narrow reason: no other plan beats it on biodiversity and stability at "
      "the same time.")

    P("The knee point is a profit maximum, not a transition target. It holds the highest yield, "
      "the lowest pest biomass and the highest stability on the front, and it reaches them only by "
      "spraying herbicide at 0.87 and insecticide at 0.94 across most of the farm, which is why its "
      "Shannon index is the lowest of the 150 plans. The same front holds a low-input alternative. "
      "Sample 1 (S1) uses herbicide 0.05, insecticide 0.01, mechanical weeding 0.23 and an edge "
      "share of 0.14, keeps 43% of the area organic and installs bat houses; the effective "
      "intensities are 0.026 for herbicide and 0.005 for insecticide. It returns 8620 CNY ha^-1 "
      "profit and 4462 kg ha^-1 seed, which is 1124 CNY and 846 kg below the knee point, with pest "
      "biomass 1.37 g C m^-2, Shannon 0.845, stability 0.290, soil carbon 1824 g C m^-2 and cost "
      "305 CNY ha^-1. The knee point converts roughly three times the input budget into 13% more "
      "profit and 19% more seed, and it pays 0.10 of Shannon and 0.07 of stability for them. Both "
      "plans are non-dominated. One answers how much profit the field can carry; the other answers "
      "how little input most of that profit needs.")
    H2("7.3 Six impact categories")
    PS("The six categories do not move independently.")

    P("Table 8 maps the six categories required by the problem onto the simulated indicators. Pest "
      "control is read from pest biomass, crop health from crop biomass, plant reproduction from "
      "the fruit-set factor, biodiversity from the Shannon index, long-term sustainability from "
      "soil organic carbon, and cost effectiveness from cost and profit. The ranges across the 150 "
      "plans are wide where the bat-house decision changes and narrow within each regime: pest "
      "biomass spans 0.085 to 3.07 g C m^-2, crop biomass 203.2 to 255.8, the fruit-set factor "
      "0.983 to 1.000, the Shannon index 0.745 to 0.876, and soil carbon 1711 to 1863 g C m^-2. "
      "Profit spans 5893 to 10026 CNY ha^-1 and cost 98 to 872 CNY ha^-1. Pest biomass separates "
      "into two clusters, 0.085 to 1.37 with bat houses and 2.4 to 3.07 without, so a single mean "
      "would describe neither.")

    TABLE([
        ["Impact category", "Indicator", "Knee-point value", "Across 150 plans", "Preferred direction"],
        ["Pest control", "Pest biomass (g C m^-2)", "0.085", "0.085-3.07", "lower"],
        ["Crop health", "Crop biomass (g C m^-2)", "255.8", "203.2-255.8", "higher"],
        ["Plant reproduction", "Fruit-set factor", "1.000", "0.983-1.000", "higher"],
        ["Biodiversity", "Shannon index", "0.745", "0.745-0.876", "higher"],
        ["Long-term sustainability", "Soil carbon (g C m^-2)", "1739", "1711-1863", "higher"],
        ["Cost effectiveness", "Cost / profit (CNY ha^-1)", "872 / 9744", "98-872 / 5893-10026", "lower cost"],
    ], "Table 8. The six impact categories, the knee-point plan, and the range across all plans.")

    P("Most of these ranges are narrow inside a regime and wide between regimes, so one indicator "
      "would give a false impression of precision. The knee point sits at one end of the "
      "biodiversity range and the low-profit plans at the other. The component analysis in the next "
      "subsection shows which management variables can still move the system, and which are flat by "
      "construction.")

    H2("7.4 Component effects")
    P("Figure 16 holds six decision variables at their knee-point values and moves the seventh to "
      "its lower and upper bound. The bat-house switch dominates. Setting u_B to zero lowers yield "
      "from 5308 to 3431 kg ha^-1 (-35%), raises pest biomass to 2.20 g C m^-2, and takes profit "
      "from 9744 to 6109 CNY ha^-1. Insecticide is second: removing it entirely lowers yield to "
      "4628 kg ha^-1 (-12.8%) and lets pest biomass rise to 1.23 g C m^-2. The organic area share "
      "acts through the premium and the conventional area. At zero it leaves yield slightly higher, "
      "5320 kg ha^-1, and profit at 9700 CNY ha^-1; at one it lowers yield to 4461 kg ha^-1 (-16%) "
      "and profit to 8560 CNY ha^-1 as herbicide and its conventional share disappear. Mechanical "
      "weeding moves soil carbon from 1855 to 1719 g C m^-2 and cost by 156 CNY ha^-1. Edge share "
      "moves biodiversity from 0.738 to 0.755 and cost by 180 CNY ha^-1 without touching yield, and "
      "herbicide moves profit by about 2% and cost by 230 CNY ha^-1 across its full range.")

    FIGURE("result_q4_components.png", "Figure 16. Component effects at the knee-point plan. Each "
                                       "bar moves one decision variable to its lower or upper "
                                       "bound while the others stay fixed.", 14.0)

    P("The fertiliser share has exactly zero effect, and the reason is a model limitation, not a result: synthetic and organic fertiliser are assigned the same nitrogen content, and "
      "the cost model does not charge for fertiliser, so the share changes neither growth nor "
      "profit. Giving organic fertiliser a slower release or a price premium would make this "
      "variable informative. We flag it here so the flat bar is not read as evidence that "
      "fertiliser choice does not matter.")
    # ================= 8 Validation =================
    H1("8. Validation and Sensitivity")
    H2("8.1 Numerical validation")
    P("Numerical accuracy was checked in two ways. Halving the integration step changed key annual "
      "means by at most 0.79%, and a one-year Radau integration agreed with the production solver to "
      "a median of 0.13%. The largest difference, 1.79%, occurred for predatory arthropods, whose "
      "annual mean is sensitive to the timing of spray pulses. The seasonal cycle converged to a "
      "fixed point of the one-year map with residual below 5.5e-8, and the annual map gave a "
      "spectral radius of 0.96 with residual 4.0e-9 under three finite-difference steps.")

    H2("8.2 Limitations")
    P("The model has clear limits. It is spatially aggregated, so it cannot resolve field-scale "
      "refuges. It does not model resistance evolution. Rodents enter only as a constant prey "
      "source, not as a dynamic population. Several parameters are calibrated because direct "
      "measurements are unavailable. These limits bound the quantitative claims, not the ranking "
      "of strategies.")

    H2("8.3 Sensitivity")
    P("We perturbed eight parameters by 20% in each direction and reran the baseline field for six "
      "years. The crop carrying capacity dominates: yield moves by -20.2% and +29.3%, and pest "
      "biomass by -26.0% and +18.8%. The pest attack rate is next, with yield changing by +14.2% "
      "and -3.6%. The bat attack rate changes yield by +6.5% and +2.0% and pest biomass by +9.9% "
      "and -18.2%. Figure 17 ranks the eight parameters by the size of their effect on yield and "
      "on pest biomass.")

    FIGURE("result_q1_sensitivity.png", "Figure 17. One-factor sensitivity. Yield (left) and pest "
                                       "biomass (right) under 20% parameter changes, as relative "
                                       "change from the baseline.", 14.0)

    P("Four parameters barely matter. The pollinator efficiency changes yield by about 1.5%, and "
      "litter decay, the nitrogen half-saturation and the seed supply each change it by less than "
      "1%. The bat attack rate is not monotone: more bat predation lowers pests but also lowers "
      "the predator community that shares the same prey, so yield can move in either direction. "
      "We therefore report the range. The rodent source has "
      "negligible influence on the baseline, which is expected because raptors are rare there; it "
      "matters only where raptors are present.")
    # ================= 9 Discussion =================
    H1("9. Discussion")
    H2("9.1 What limits the system")
    P("The four questions share one answer: the system is limited by its slowest component. In the "
      "first question the limiting component is the predator community, which trails the pest peak "
      "by several weeks. In the second it is soil nitrogen, which earthworms accelerate but raptors "
      "do not touch. In the third it is pest suppression, which bats provide and parasitoids cannot: "
      "the bat-house plan cuts pest biomass from 2.79 to 1.17 g C m^-2, while the fruit-set factor "
      "moves only from 0.978 to 0.995. In the fourth it is the transition cost, which determines "
      "whether an ecologically superior plan is financially feasible. This reading also explains why "
      "single-input policies disappoint. Removing a chemical without "
      "replacing its function leaves a gap that pests fill. Removing a predator without accounting "
      "for its prey releases the prey. The model does not say that chemicals are bad or that organic "
      "farming is good. It says that each input performs a function, and that the function has to be "
      "replaced before the input is removed.")

    H2("9.2 From results to practice")
    P("For the farmer's letter, the practical implication is an ordering. Protect the bats and the "
      "flowering margins first, because this adds a function that no spray provides. Cut insecticide "
      "and release natural enemies in the same season, because the release covers the suppression "
      "the spray was buying; the bat-house sweep shows that suppression arrives as a threshold, so "
      "the two steps have to move together. Reduce herbicide last, because the crop compensates for "
      "the extra weeds and the risk is concentrated in two seasons. The ordering points to S1, not "
      "to the knee point. S1 spends 305 CNY ha^-1 on inputs and returns 8620 CNY ha^-1 with 4462 "
      "kg ha^-1 of seed, because almost no herbicide or insecticide remains on its conventional "
      "area. The profit maximum reaches 9744 CNY ha^-1 and 5308 kg ha^-1, but only with herbicide "
      "at 0.87 and insecticide at 0.94 and an input bill of 872 CNY ha^-1, so it is a ceiling, not "
      "a target. A fully organic area lowers yield by 16% at the knee point, from 5308 to 4461 "
      "kg ha^-1, and the premium has to cover that gap. "
      "The organic meta-analysis [7] reports a yield gap of comparable size but a gain in "
      "year-to-year stability, which our conversion case does not reproduce. Two features of the "
      "crop explain the difference. An oilseed crop is partly pollinator-dependent, so a plan that "
      "protects bats and flowering margins recovers part of the gap that a herbicide-only conversion "
      "cannot. A half-dose insecticide regime is the trap in between: it still suppresses the "
      "natural enemies that would replace the spray, and it does not remove the pest pressure, so "
      "the farm pays both costs. The model therefore supports full conversion with replacement, not "
      "a partial withdrawal.")

    H2("9.3 Model evaluation")
    P("The model is strongest where the problem is structural and weakest where it is spatial. "
      "Table 9 separates the two. The seasonal formulation and the chemical residue model are "
      "supported by the numerical checks in Section 8, while the one-field abstraction and the "
      "calibrated parameters limit what can be claimed about a specific farm.")

    TABLE([
        ["Aspect", "Evidence", "Consequence"],
        ["Seasonality", "Floquet radius 0.576; annual-map radius 0.96", "Cycle is stable, so scenarios differ in composition"],
        ["Chemical detail", "Residue half-lives of 20 and 8 days", "Withdrawal is gradual, with a legacy tail"],
        ["Species resolution", "Three ablations and a no-bat baseline", "The bat effect is an attribution, not one coefficient"],
        ["Spatial resolution", "One field plus an edge strip", "Field-scale refuges are not resolved"],
        ["Parameter provenance", "Most values calibrated", "Quantitative claims are conditional"],
        ["Management realism", "Seven management variables", "Most farmer choices are represented"],
        ["Validation coverage", "Floquet, annual map, solver cross-check", "Numerical behaviour is checked, field data are not"],
    ], "Table 9. Model evaluation: what the structure supports and what it does not.")

    P("The table is a reading guide. It marks where a reader should trust a number and where a "
      "number should be read as a direction. The seasonal and chemical results sit in the first "
      "category. The organic frontier sits in the second, because its position depends on prices "
      "and on calibrated yields.")

    # ================= 10 Letter =================
    PAGEBREAK()
    H1("10. Letter to a Farmer")
    DOC.paragraphs[-1].paragraph_format.space_before = pf.Pt(24)
    P("Dear farmer,")
    P("You asked whether it is worth reducing chemicals and moving toward organic practices. Our "
      "model of a converted forest field suggests that it is, but not all at once and not without a "
      "plan.")
    P("Start with bats. In our simulations, a field that stopped using herbicide yielded 3153 "
      "kg per hectare, and the same field with bat roosts and flowering margins yielded 4783 "
      "kg per hectare while pest biomass fell from 2.79 to 1.17 g C per square metre. A field "
      "without bats yielded 2822 kg per hectare. The practical step is cheap: keep or install "
      "roosts, leave flowering margins, and avoid night spraying during flowering.")
    P("Then cut insecticide and put natural enemies back in the same season. Insecticide on its "
      "own lowered the predators from 0.66 to 0.46 g C per square metre, raised the pest "
      "variability from 1.90 to 2.42, and left the yield at 3424 kg per hectare against 3506 "
      "without inputs. The spray was taking pest control with one hand and removing the predators "
      "with the other. A parasitoid release under a reduced dose reached 3412 kg per hectare, so "
      "the replacement works when the two steps move together.")
    P("Herbicide can wait until last. Weeds rose by about 20%, from 8.01 to 9.63 g C per square "
      "metre, and yield held at 3153 kg per hectare. The crop compensated. The risk sits in the "
      "first two seasons, so plan mechanical weeding and a cover crop for that window.")
    P("The economics depend on the premium. Our balanced plan sprays herbicide at 0.05 and "
      "insecticide at 0.01, keeps 43% of the area organic, installs bat houses, and spends 305 CNY "
      "per hectare on inputs. It returns 8620 CNY per hectare with 4462 kg per hectare of seed, "
      "pest biomass of 1.37 g C per square metre and 1824 g C per square metre of soil carbon. A "
      "profit-maximising plan reaches 9744 CNY and 5308 kg per hectare, but it sprays herbicide at "
      "0.87 and insecticide at 0.94 on the 88% of the area that stays conventional, and its input "
      "bill is 872 CNY per hectare; treat it as a ceiling, not as a route. A fully organic area "
      "costs 16% of the yield at that ceiling, from 5308 to 4461 kg per hectare, so the premium has "
      "to cover the gap. During the three-year conversion you will not receive it, so you need "
      "working capital equal to roughly one season of input cost. Plans that skip the bat houses "
      "earn about 7000 CNY per hectare and hold the most biodiversity, but they yield only about "
      "3560 kg per hectare.")
    P("If I were advising one change for next season, it would be this: protect the bats and the "
      "flowering margins first, then cut insecticide and release natural enemies together, and "
      "reduce herbicide last. The first step adds a function. The last step removes the least.")
    P("Sincerely,")
    P("The modelling team")
    # ================= References =================
    H1("References")
    DOC.paragraphs[-1].paragraph_format.space_before = pf.Pt(18)
    refs = [
        "Maas B., Clough Y., Tscharntke T. (2013). Bats and birds increase crop yield in tropical agroforestry landscapes. Ecology Letters 16, 1480-1487. doi:10.1111/ele.12194",
        "Gras P., Tscharntke T., Maas B. et al. (2016). How ants, birds and bats affect crop yield along shade gradients in tropical cacao agroforestry. Journal of Applied Ecology 53, 953-963. doi:10.1111/1365-2664.12625",
        "Bieg C., Gellner G., McCann K.S. (2023). Stability of consumer-resource interactions in periodic environments. Proceedings of the Royal Society B 290. doi:10.1098/rspb.2023.1636",
        "Beringue A., Queffelec J., Le Lann C., Sulmon C. (2024). Sublethal pesticide exposure in non-target terrestrial ecosystems. Environmental Research 260, 119620. doi:10.1016/j.envres.2024.119620",
        "Macgregor C.J., Scott-Brown A.S. (2020). Nocturnal pollination: an overlooked ecosystem service. Emerging Topics in Life Sciences 4, 19-32. doi:10.1042/etls20190134",
        "Zamora-Gutierrez V. et al. (2021). Vulnerability of bat-plant pollination interactions due to environmental change. Global Change Biology 27, 3367-3382. doi:10.1111/gcb.15611",
        "Knapp S., van der Heijden M.G.A. (2018). A global meta-analysis of yield stability in organic and conservation agriculture. Nature Communications 9, 3632. doi:10.1038/s41467-018-05956-1",
        "Winter S. et al. (2018). Effects of vegetation management intensity on biodiversity and ecosystem services in vineyards: a meta-analysis. Journal of Applied Ecology 55, 2484-2495. doi:10.1111/1365-2664.13124",
        "Pandey S., Johnson A.C., Xie G., Gurr G.M. (2022). Pesticide regime can negate the positive influence of native vegetation donor habitat on natural enemy abundance. Frontiers in Ecology and Evolution 10. doi:10.3389/fevo.2022.815162",
        "Litovska I., van der Plas F., Kleijn D. (2025). Arthropod abundance is most strongly driven by crop and semi-natural habitat type. Agriculture, Ecosystems and Environment 378, 109298. doi:10.1016/j.agee.2024.109298",
        "Buhler D.D., Gunsolus J.L., Ralston D.F. (1992). Integrated weed management techniques to reduce herbicide inputs in soybean. Agronomy Journal 84, 973-978. doi:10.2134/agronj1992.00021962008400060013x",
        "Popp J., Peto K., Nagy J. (2013). Pesticide productivity and food security: a review. Agronomy for Sustainable Development 33, 243-255. doi:10.1007/s13593-012-0105-x",
        "Braun de Torrez E.C. et al. (2019). Sympatric bat species prey opportunistically on a major moth pest of pecans. Sustainability 11, 6365. doi:10.3390/su11226365",
        "Latino D.A.R.S. et al. (2017). Eawag-Soil in enviPath: regulatory pesticide soil biodegradation pathways and half-life data. Environmental Science: Processes and Impacts 19, 449-464. doi:10.1039/c6em00697c",
    ]
    for i, r in enumerate(refs, 1):
        pf.paragraph(DOC, f"[{i}] {r}")

    PAGEBREAK()
    H1("AI Use Report")
    P("This work used an AI assistant at several stages. The coding assistant was Claude Code, "
      "running Claude models, with Python 3.13, numpy, pandas, matplotlib, scipy and PyMuPDF. AI "
      "support covered five tasks: literature discovery, code generation, numerical experiment "
      "design, figure production and manuscript drafting.")

    P("Representative requests were: find peer-reviewed studies on bat and bird pest suppression "
      "and on organic yield stability; implement a seasonally forced food-web model with residue "
      "dynamics and Floquet analysis; add channel ablations, Latin-hypercube sampling and a "
      "one-factor sensitivity analysis; produce publication figures with a fixed style; and revise "
      "the manuscript for clarity. The assistant wrote code, ran it, and returned CSV tables and "
      "figures, which the authors inspected.")

    P("All numerical results were produced by the executed scripts and checked against the reported "
      "tables; the two ratio and residual values were recomputed from the result files. Model "
      "outputs were checked against the CSV files, "
      "figures were audited by a script for size, resolution and text, and all 14 references were "
      "matched to DOI records. The AI did not generate data, invent results or add citations. The "
      "authors reviewed and edited the manuscript and take responsibility for its content.")
    out = ROOT / "完整论文.docx"
    DOC.save(out)
    return out


if __name__ == "__main__":
    import json
    mp = ROOT / "results" / "toc_pages.json"
    if mp.exists():
        PAGES_MAP = json.loads(mp.read_text(encoding="utf-8"))
    path = build()
    print("saved", path)
