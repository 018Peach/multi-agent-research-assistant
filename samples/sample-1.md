# Sample run — CX multimodal, two turns

A real captured session demonstrating the **multimodal CX** use case and **follow-up continuity**:
turn 1 attaches a complaints chart; turn 2 builds on it (no chart re-upload, no re-run of vision).

**Attached visual (turn 1):**
an Ofcom chart of UK mobile providers' customer-service / complaint metrics.

---

## Turn 1

**Input:**
> Using the attached chart, which UK mobile providers look worst for customer complaints, and what
> should a worst-performing operator do to improve?

**Output:**

Based on the provided data and industry analysis, three UK mobile providers stand out for poor
performance in specific complaint categories:

- **O2:** Shows the highest volume of regulatory escalations, with 23 Ofcom complaints per 100,000
  subscribers — nearly double the industry average of 12 (chart). Contractual issues and unexpected
  price rises are the primary drivers of these escalations (Ofcom; Telecoms.com).
- **Three:** Records the lowest satisfaction with complaint handling at 51%, significantly below the
  61% sector average (chart).
- **Sky:** Has the highest internal dissatisfaction rate, with 19% of customers reporting a reason
  to complain, compared to the 14% average (chart).

To improve performance, worst-performing operators should implement the following strategies:

**1. Optimize complaint handling and resolution**
- **Prevent information repetition:** A major driver of dissatisfaction is customers having to
  repeat details. Best practice involves ensuring the first handler logs the complaint immediately
  to provide a seamless transition if the case is escalated (Ofcom Qualitative Insight).
- **Mandatory staff training:** Under General Condition C4.3, providers must ensure all
  customer-facing staff are trained in specific complaint-handling procedures and how to refer
  customers to specialist teams (Ofcom General Conditions).
- **Accelerate ADR timelines:** While current rules mandate an Alternative Dispute Resolution (ADR)
  letter after eight weeks of no resolution, Ofcom is shortening this period to six weeks effective
  8 April 2026 (Ofcom ADR Rules). Operators should utilize Senior Resolution teams to intercept and
  resolve cases before these deadlines (Comms Ombudsman).

**2. Increase billing and contract transparency**
- **Standardized price rises:** To mitigate complaints about "unexpected" costs, providers should
  move away from inflation-linked increases toward a "pounds and pence" format, as now required by
  Ofcom (BBC).
- **Proactive bill management:** Implementing mandatory spend caps can prevent "bill shock" from
  roaming or data overages, reducing the initial reason to complain (Ofcom Bill Limits).

**3. Address service and accessibility root causes**
- **Proactive network maintenance:** Using AI and automation for fault detection can resolve network
  reliability issues before they impact the customer (Mobile World Live).
- **Accessibility compliance:** To support vulnerable subscribers, operators must ensure complaint
  procedures are available in accessible formats such as large print or Braille, as per General
  Condition C4.10 (Ofcom General Conditions).

**Sources**
1. A primary driver of customer dissatisfaction in the UK mobile sector is the need to repeat complaint details across multiple calls; best practice involves ensuring the first handler correctly logs the complaint to provide a seamless transition if escalation is required. — www.ofcom.org.uk
2. As of July 2024, the UK Telecommunications & Media sector saw a significant drop in complaint handling satisfaction, falling 6.2 points to a score of 53.3 out of 100. — www.ispreview.co.uk
3. Ofcom General Condition C4 mandates that UK mobile providers must issue an Alternative Dispute Resolution (ADR) letter if a complaint remains unresolved after eight weeks. — www.ofcom.org.uk
4. Effective 8 April 2026, Ofcom is reducing the mandatory waiting period for customers to escalate unresolved complaints to an Alternative Dispute Resolution (ADR) scheme from 8 weeks to 6 weeks. — www.ofcom.org.uk
5. General Condition C4.3 requires telecommunications providers to ensure all staff who interact with customers are specifically trained on complaint handling procedures and referring consumers to specialist teams. — www.ofcom.org.uk
6. Immediate logging of complaints at the point of first contact is an operational step that reduces 'complaints about complaint handling' by preventing customers from repeating issues on subsequent calls. — www.ofcom.org.uk
7. Providers can use 'Deadlock Letters' to trigger ADR earlier if they cannot resolve a case, but operational efficiency focuses on intercepting cases via Senior Resolution teams before reaching the 6-week deadline. — www.commsombudsman.org
8. Operationalizing transparent and early communication regarding price rises is critical to reducing complaint volumes, as 'unexpected' changes are a primary driver of escalations to Ofcom. — www.telecoms.com
9. General Condition C4.10 mandates that complaint procedures must be accessible to disabled customers, including provision in formats like large print or Braille, to ensure compliance for vulnerable subscribers. — www.ofcom.org.uk
10. Mid-contract price rises are a significant driver of increased mobile customer complaints in the UK. — www.ofcom.org.uk
11. Ofcom has implemented a ban on inflation-linked price rises, requiring providers to use 'pounds and pence' for future increases. — www.bbc.com
12. Contractual issues are a primary root cause of complaints for major UK mobile providers like O2. — www.ofcom.org.uk
13. Mandatory spend caps serve as a proactive solution to prevent 'bill shock' from unexpected mobile charges. — www.ofcom.org.uk
14. The Shared Rural Network (SRN) initiative targets network reliability issues by aiming for 95% UK 4G coverage by 2025. — www.gov.uk
15. Mobile operators are using AI and automation for proactive fault detection to mitigate network reliability issues. — assets.mobileworldlive.com

---

## Turn 2 (follow-up — same session, no chart re-upload)

**Input:**
> Based on each operator's strengths and weaknesses from the chart, how could UK mobile providers
> collaborate — e.g. network/infrastructure sharing, shared anti-fraud, industry initiatives — to
> improve overall service quality?

**Output:**

Based on the performance metrics of UK mobile operators, collaboration through infrastructure
sharing, fraud prevention, and technology initiatives could address specific weaknesses in
reception and complaint volumes.

**1. Infrastructure sharing to close the reception gap**
With O2 (73%) and Three (70%) lagging behind leaders in reception satisfaction (chart), network
collaboration is a primary lever for improvement:
- **Shared Rural Network (SRN):** Under the "Partial Not-Spot" (PNS) phase of the SRN, O2 and Three
  are specifically permitted to share EE's existing infrastructure to rapidly close 4G coverage gaps
  (GOV.UK).
- **Neutral host models:** To achieve true signal parity, operators can adopt "neutral host" models
  like the Boldyn Networks project on the London Underground, which provides a single shared
  infrastructure for all four major networks (Boldyn).
- **Limitations of current sharing:** While joint ventures like MBNL (EE/Three) and Cornerstone
  (O2/Vodafone) facilitate site sharing, they do not guarantee equal performance due to different
  spectrum holdings (Ofcom). Proposed updates, such as those in the Vodafone-Three merger, aim to
  further consolidate mast portfolios to improve signal density (VodafoneThree).

**2. Industry-wide anti-fraud and billing accuracy**
O2's high rate of regulatory escalations (23 complaints per 100k) (chart) suggests a need for
tighter control over fraud-related billing disputes:
- **Cross-sector data sharing:** Virgin Media O2 (VMO2) participates in the 'Scam Signal'
  initiative, collaborating with UK Finance and major banks to use network data for real-time
  detection of Authorised Push Payment (APP) fraud (GSMA).
- **Shared defensive tools:** Operators utilize the '7726' reporting service to identify and block
  malicious texts; VMO2 alone has blocked over 92 million such messages to prevent fraudulent
  billing (VMO2 News). Additionally, the '159' service, launched by 'Stop Scams UK', allows
  customers to safely verify calls from banks, reducing social engineering risks (Stop Scams UK).
- **Regulatory compliance:** To reduce billing errors, O2 undergoes mandatory annual audits of its
  Total Metering and Billing Systems (TMBS) to ensure compliance with Ofcom accuracy standards (TUV
  SUD). They also collaborate with Ofcom to block spoofed international calls (Ofcom/VMO2).

**3. Shared technology for customer service**
The data shows Three struggling with complaint handling satisfaction (51%) and Sky seeing high
internal complaint rates (19%) (chart):
- **Global Telco AI Alliance:** A UK-based joint venture has been established to develop shared,
  multilingual AI customer service technology for the industry (TelecomTV; Mobile Europe).
- **Shift from proprietary to shared models:** While many UK providers currently treat AI support as
  a proprietary differentiator (BT Group), adopting the digital-first and community-led support
  models used by top-rated MVNOs like giffgaff could help larger MNOs improve their response times
  and satisfaction scores (Mobile News).

**Sources**
1. The Shared Rural Network (SRN) "Partial Not-Spot" (PNS) phase specifically targets the 4G coverage gap by allowing O2 and Three to share EE's existing infrastructure. — www.gov.uk
2. Neutral host models, such as the Boldyn Networks London Underground project, enforce signal parity by providing a single shared infrastructure for all four MNOs. — www.boldyn.com
3. Infrastructure sharing through MBNL (EE/Three) and Cornerstone (O2/Vodafone) focuses on site-sharing but does not guarantee performance parity due to differing spectrum holdings. — www.ofcom.org.uk
4. Proposed mergers and agreement updates (e.g., Vodafone-Three) aim to consolidate mast portfolios to improve density and signal consistency. — www.vodafonethree.com
5. Virgin Media O2 (VMO2) participates in 'Scam Signal', a cross-industry initiative with UK Finance and major banks that uses mobile network data to detect Authorised Push Payment (APP) fraud in real-time. — www.gsma.com
6. O2 utilizes the industry-standard '7726' reporting service, which has enabled Virgin Media O2 to block over 92 million malicious texts to prevent fraud-related billing disputes. — news.virginmediao2.co.uk
7. O2 is a member of 'Stop Scams UK', a collaborative group of telcos and banks that launched the '159' service to help customers verify bank calls and prevent social engineering scams. — stopscamsuk.org.uk
8. O2 undergoes mandatory annual 'Total Metering and Billing Systems' (TMBS) audits conducted by third-party approval bodies to ensure compliance with Ofcom's billing accuracy regulations. — www.tuvsud.com
9. Virgin Media O2 actively collaborates with Ofcom on 'Calling Line Identification' (CLI) accuracy initiatives to block spoofed international calls, a major source of fraudulent activity and complaints. — www.ofcom.org.uk
10. A major global Joint AI venture has been established to develop shared customer service technology for telecommunications providers. — www.mobileeurope.co.uk
11. The Global Telco AI Alliance venture is registered as a UK-based entity, facilitating collaborative AI development within the UK. — www.telecomtv.com
12. UK MNOs currently invest in customer service AI as a proprietary differentiator rather than sharing platforms across the industry. — newsroom.bt.com
13. Top-rated MVNOs achieve higher service quality by utilizing digital-first and community-led support models. — mobilenewscwp.co.uk
