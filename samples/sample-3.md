# Sample run — general research (text-only, health domain)

Another **non-CX, text-only** run, in an evidence-sensitive domain — a good showcase of the
grounding guardrail (the critic really earns its keep on medical claims; every statement is tied
to a clinical/regulatory source).

---

## Input
> What does current evidence say about GLP-1 drugs (e.g. semaglutide) for weight loss — efficacy,
> common side effects, and who they're not recommended for?

## Output

Current clinical evidence demonstrates that GLP-1 receptor agonists are highly effective for weight
loss, with tirzepatide generally showing greater potency than semaglutide. However, these
medications carry significant gastrointestinal risks and specific medical contraindications.

**Efficacy and weight-loss outcomes**
Clinical trials indicate that both semaglutide and tirzepatide facilitate substantial weight
reduction that can be sustained over several years:
- **Semaglutide (e.g., Wegovy):** In the STEP 1 trial, a once-weekly 2.4 mg dose led to a mean
  weight loss of 14.9% over 68 weeks (source). This loss is largely maintained over time, with the
  STEP 5 trial showing a 15.2% mean reduction at 104 weeks (source).
- **Tirzepatide (e.g., Zepbound):** This medication, which targets both GLP-1 and GIP receptors, has
  shown higher efficacy in trials. The SURMOUNT-1 trial reported a 20.9% mean weight reduction at 72
  weeks for the 15 mg dose (source). Long-term data over 176 weeks (3 years) showed a sustained mean
  weight loss of 22.9% in adults with obesity and prediabetes (source).
- **Comparative efficacy:** In a head-to-head trial (SURMOUNT-5), tirzepatide was found to be
  superior to semaglutide, resulting in a 20.2% weight loss compared to 13.7% for semaglutide over
  72 weeks (source).

**Common and serious side effects**
While effective, these drugs are associated with several adverse effects:
- **Gastrointestinal issues:** These are the most frequent side effects. Nausea affects more than
  44% of patients using semaglutide (source). Users also face a significantly increased risk of
  gastroparesis (stomach paralysis) (source).
- **Pancreatitis and gallbladder disease:** Semaglutide is linked to a higher risk of acute
  pancreatitis, with a hazard ratio of 9.09 compared to other weight-loss treatments (source).
  Additionally, medications like Wegovy increase the risk of gallbladder inflammation and gallstones
  (source).
- **Body-composition changes:** Weight loss from these drugs includes a reduction in lean body mass.
  Muscle loss accounts for approximately 40% of the total weight lost with semaglutide and 25% with
  tirzepatide (source).

**Contraindications and recommendations**
GLP-1 medications are not recommended for everyone due to specific safety concerns:
- **Thyroid-cancer risk:** They are strictly contraindicated in patients with a personal or family
  history of Medullary Thyroid Carcinoma (MTC) or Multiple Endocrine Neoplasia syndrome type 2
  (MEN 2) (source; source).
- **Pregnancy:** These drugs are not recommended during pregnancy and must be discontinued if
  pregnancy occurs. Semaglutide should be stopped at least two months before a planned pregnancy
  (source).
- **Existing medical conditions:**
  - Generally not recommended for patients with a history of pancreatitis or severe gastrointestinal
    diseases like gastroparesis (source; source).
  - Patients with type 2 diabetes and diabetic retinopathy require close monitoring, as rapid
    improvements in glucose control can temporarily worsen eye conditions (source).

**Sources**
1. In the STEP 1 clinical trial, once-weekly semaglutide 2.4 mg resulted in a mean weight loss of 14.9% from baseline at 68 weeks. — www.nejm.org
2. The STEP 5 trial showed that weight loss with semaglutide 2.4 mg is sustained over 104 weeks (2 years), with a mean weight loss of 15.2%. — www.nature.com
3. In the SURMOUNT-1 trial, tirzepatide at its highest dose (15 mg) led to a mean weight reduction of 20.9% at 72 weeks. — www.nejm.org
4. The SURMOUNT-5 head-to-head trial found tirzepatide superior to semaglutide 2.4 mg, with mean weight losses of 20.2% and 13.7% respectively at 72 weeks. — www.nejm.org
5. Long-term treatment with tirzepatide (15 mg) for 3 years (176 weeks) maintained a mean weight loss of 22.9% in adults with obesity and prediabetes. — www.nejm.org
6. Gastrointestinal adverse events are the most frequent side effects of semaglutide, with nausea affecting over 44% of patients in clinical trials. — www.nejm.org
7. Weight loss from GLP-1 medications includes significant reductions in lean body mass, with muscle loss accounting for approximately 40% of total weight lost in semaglutide trials and 25% in tirzepatide trials. — www.ahajournals.org
8. GLP-1 receptor agonists are associated with a significantly increased risk of gastroparesis compared to non-GLP-1 weight loss medications. — jamanetwork.com
9. Use of semaglutide for weight loss is linked to a higher risk of acute pancreatitis, with research indicating a hazard ratio of 9.09 compared to other weight loss treatments. — jamanetwork.com
10. GLP-1 medications like Wegovy increase the risk of gallbladder disease, including gallstones and inflammation of the gallbladder. — www.accessdata.fda.gov
11. GLP-1 receptor agonists for weight loss are strictly contraindicated in patients with a personal or family history of Medullary Thyroid Carcinoma (MTC) due to a potential risk of thyroid C-cell tumors. — www.accessdata.fda.gov
12. Use of GLP-1 weight loss medications is contraindicated in patients with Multiple Endocrine Neoplasia syndrome type 2 (MEN 2). — www.accessdata.fda.gov
13. GLP-1 medications for weight loss are not recommended during pregnancy and should be discontinued if pregnancy occurs; semaglutide specifically should be stopped 2 months before a planned pregnancy. — www.accessdata.fda.gov
14. GLP-1 receptor agonists for weight loss are generally not recommended for patients with a history of pancreatitis and must be discontinued if acute pancreatitis is suspected. — www.accessdata.fda.gov
15. Patients with type 2 diabetes and a history of diabetic retinopathy require monitoring when taking GLP-1 drugs as rapid glucose control can temporarily worsen the condition. — www.accessdata.fda.gov
16. GLP-1 receptor agonists are not recommended for patients with severe gastrointestinal disease, such as gastroparesis, due to their mechanism of delaying gastric emptying. — www.accessdata.fda.gov
