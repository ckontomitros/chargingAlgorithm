# Diploma Thesis Summary

## Title
**Smart Electric Vehicle Charging in Office Buildings: A Multi-Level Intelligence Approach with Renewable Energy Integration**

---

## Overview

This diploma thesis investigates intelligent electric vehicle (EV) charging systems for office buildings with integrated solar photovoltaic (PV) systems. The research compares four distinct intelligence levels, from basic uncontrolled charging to advanced optimization algorithms with Vehicle-to-Grid (V2G) capability.

### Research Context

- **Application Domain:** Office buildings with workplace EV charging
- **Fleet Size:** 15 electric vehicles
- **Renewable Integration:** 150 m² solar PV system (30 kW peak)
- **Grid Constraints:** 80 kW capacity limit
- **Optimization Objective:** Minimize electricity costs while meeting mobility requirements

---

## Intelligence Levels Investigated

### Level 0: Baseline (Uncontrolled Charging)
- **Description:** EVs charge immediately at maximum rate upon connection
- **Characteristics:** No coordination, simple implementation
- **Expected Performance:** Highest cost, potential grid violations, poor solar utilization
- **Purpose:** Baseline for comparison

### Level 1: Simple Rule-Based Charging
- **Description:** Heuristic algorithm with priority-based allocation
- **Rules:**
  1. Use building solar surplus first
  2. Then use grid within capacity limits
  3. First-come, first-served among EVs
- **Characteristics:** Low complexity, predictable, reasonably effective
- **Expected Performance:** Significant cost savings vs. Level 0, respects constraints

### Level 2: Intelligent Optimization Algorithms
- **Description:** Advanced algorithms that compute/learn optimal charging schedules
- **Algorithms Implemented:**
  1. **Reinforcement Learning (Q-Learning):** Learns optimal policy through trial and error
  2. **Model Predictive Control (MPC):** Receding horizon optimization
  3. **Particle Swarm Optimization (PSO):** Nature-inspired swarm intelligence
  4. **Mixed Integer Linear Programming (MILP):** Mathematical optimization (globally optimal)
  5. **Deep Q-Network (DQN):** Neural network-based RL
- **Characteristics:** Near-optimal performance, higher computational requirements
- **Expected Performance:** Best cost savings, maximum solar utilization

### Level 3: Vehicle-to-Grid (V2G)
- **Description:** Bidirectional energy flow - EVs can discharge back to grid/building
- **Capabilities:**
  - Charge during low-price hours
  - Discharge during high-price hours
  - Energy arbitrage and grid services
- **Characteristics:** Additional infrastructure required, revenue generation potential
- **Expected Performance:** Additional economic benefits, but increased battery cycling

---

## Methodology

### System Components

#### 1. Office Building
- **Energy Consumption:** Hourly profile from real office building data
  - Baseline: ~3 kW (overnight)
  - Peak: ~8-10 kW (business hours)
  - Total daily: ~XXX kWh
  
- **Solar PV System:**
  - Panel area: 150 m²
  - Efficiency: 20%
  - Peak power: 30 kW
  - Data source: PVGIS (European Commission)
  
- **Building Battery:**
  - Capacity: 80 kWh
  - Efficiency: 95%
  - Max charge/discharge: 50 kW

#### 2. Electric Vehicle Fleet
- **Fleet:** 15 vehicles (Tesla Model 3 equivalent)
- **Battery:** 100 kWh per vehicle
- **Charging:** 22 kW (Level 2 AC charger)
- **Discharging:** 22 kW (V2G capable)
- **Mobility Pattern:**
  - Arrival: 6-9 AM (random within window)
  - Departure: 4-8 PM (random within window)
  - Initial SoC: 20-30% (after morning commute)
  - Desired SoC: 70-80% (for evening commute)

#### 3. Grid
- **Pricing:** Time-of-use tariff
  - Peak: €0.58-0.70/kWh (early morning)
  - Off-peak: €0.18-0.30/kWh (midday, solar peak)
  - Evening: €0.25-0.55/kWh
- **Sell Prices:** €0.10-0.60/kWh (80-90% of purchase)
- **Capacity:** 80 kW hourly limit

### Optimization Problem

**Objective:** Minimize total daily electricity cost

$$\min \sum_{t=0}^{23} \left[ \pi_{buy}(t) \cdot E_{grid}(t) - \pi_{sell}(t) \cdot E_{V2G}(t) \right]$$

**Subject to:**
- All EVs reach desired SoC before departure
- SoC stays within safe bounds (20%-100%)
- Grid capacity not exceeded
- Energy balance maintained

### Algorithm Implementations

#### Reinforcement Learning (Q-Learning)
- **State:** (EV_id, SoC_bin, hour, grid_availability)
- **Actions:** {charge, standby} or {charge, discharge, standby}
- **Training:** 2,000-15,000 episodes
- **Learning rate:** 0.10-0.15
- **Reward:** Balances cost minimization, solar usage, target achievement

#### Model Predictive Control
- **Horizon:** 6-8 hours lookahead
- **Optimization:** Random perturbation method
- **Iterations:** 50-60 per hour
- **Execution:** First step of optimal plan

#### Particle Swarm Optimization
- **Particles:** 30-40
- **Iterations:** 50-60
- **Parameters:** w=0.7, c1=c2=1.5
- **Fitness:** Total cost + constraint penalties

#### Mixed Integer Linear Programming
- **Solver:** PuLP with CBC backend
- **Horizon:** Full 24 hours
- **Solution:** Globally optimal
- **Execution:** First hour of optimal schedule

#### Deep Q-Network
- **Architecture:** 64-64-32 neurons (ReLU)
- **Training:** 1,000 episodes with experience replay
- **Batch size:** 32
- **Target network:** Updated every 10 episodes

---

## Expected Results and Analysis

### Economic Performance

**Hypothesis:** Each intelligence level provides cost savings, with diminishing returns.

**Expected Findings:**
- Level 0 (Baseline): €40-50 per day
- Level 1 (Simple): €25-35 per day (30-40% savings)
- Level 2 (Optimal): €20-30 per day (40-50% savings)
- Level 3 (V2G): €15-25 per day (50-60% savings)

**Annual Projections (250 working days):**
- Level 1 savings: €2,500-3,750 per year
- Level 2 savings: €3,750-5,000 per year
- Level 3 savings: €5,000-7,500 per year

### Renewable Energy Utilization

**Expected Findings:**
- Level 0: 15-25% of charging from solar
- Level 1: 50-70% of charging from solar
- Level 2: 70-85% of charging from solar
- Level 3: 75-90% of charging from solar

**Impact:** Smart charging increases solar self-consumption by 40-60%.

### Operational Performance

**Expected Findings:**
- All intelligent methods (Levels 1-3) achieve 100% target SoC
- Level 0 may violate grid capacity 8-12 times per day
- Intelligent methods respect all constraints
- Average final SoC: 75-80% across all methods

### Algorithm Comparison

**Expected Rankings (by cost):**
1. MILP (optimal)
2. MPC (near-optimal)
3. RL (near-optimal)
4. PSO (good)
5. DQN (good, but overkill for this problem)
6. Simple (reasonable)

**Optimality Gap:**
- MPC: 1-3% from optimal
- RL: 2-5% from optimal
- PSO: 3-7% from optimal
- Simple: 15-25% from optimal

**Computational Requirements:**
- Simple: <1 second
- MPC: 5-15 seconds
- PSO: 10-20 seconds
- RL: 2-5 minutes (training) + <1 second (execution)
- MILP: 30-120 seconds
- DQN: 30-60 minutes (training) + <1 second (execution)

### V2G Impact

**Expected Findings:**
- Additional benefit: €3-8 per day
- Annual potential: €750-2,000 for 15-vehicle fleet
- Per-vehicle V2G revenue: €50-130 per year
- Discharge primarily during evening peak (4-7 PM)
- Increased battery cycling: 20-40% more throughput

**Trade-offs:**
- Revenue vs. battery degradation
- Infrastructure cost vs. benefit
- User acceptance challenges

---

## Key Contributions

### 1. Comprehensive Multi-Level Comparison

First study to systematically compare four intelligence levels with multiple algorithms in office building context.

### 2. Practical Implementation

All algorithms implemented in Python with:
- Complete source code (reproducible research)
- Realistic constraints and data
- Detailed documentation

### 3. V2G Evaluation

Quantitative assessment of V2G benefits with:
- Realistic discharge constraints
- Revenue calculation
- Battery cycling analysis

### 4. Renewable Integration Focus

Emphasis on solar PV integration:
- Temporal alignment analysis
- Self-consumption optimization
- Economic and environmental benefits

### 5. Actionable Recommendations

Clear guidance for practitioners:
- Which level to implement based on fleet size
- Algorithm selection criteria
- ROI analysis and payback periods
- Implementation roadmap

---

## Main Conclusions (Expected)

### 1. Intelligence Pays, But Diminishing Returns

- **Level 0 → Level 1:** Largest improvement (30-40% cost reduction)
- **Level 1 → Level 2:** Moderate improvement (5-15% additional)
- **Level 2 → Level 3:** Small improvement (5-10% additional)

**Implication:** Simple rule-based (Level 1) offers best cost-benefit ratio for most applications.

### 2. Algorithm Selection Depends on Context

- **Small fleets (<10 EVs):** Simple rules sufficient
- **Medium fleets (10-25 EVs):** RL or MPC recommended
- **Large fleets (>25 EVs):** RL or MILP (if computational resources available)

**Trade-off:** Optimality vs. simplicity vs. computational cost

### 3. V2G is Economically Attractive (With Caveats)

**Conditions for V2G viability:**
- Favorable sell-back prices (>80% of purchase)
- High price volatility
- Company-owned fleet (no user degradation concerns)
- Sufficient scale (>10 vehicles)

**Payback period:** 3-5 years for typical office building

### 4. Renewable Integration is Critical

- Solar PV reduces charging costs by 40-60%
- Temporal alignment: Office hours match solar production
- Smart charging increases solar self-consumption by 40-60%
- Near-zero-carbon charging during midday hours

### 5. Office Buildings are Ideal for Smart Charging

**Advantages:**
- Predictable arrival/departure patterns
- Long parking duration (7-14 hours)
- Solar PV potential (rooftop space)
- Centralized management
- Economic incentives for building owners

---

## Practical Recommendations

### For Small Office Buildings (5-10 EVs)

**Recommended:** Level 1 (Simple Rule-Based)

**Why:**
- Achieves 70-80% of maximum possible savings
- Minimal infrastructure cost (€5,000-15,000)
- Easy to implement and maintain
- Reliable and predictable
- Payback: 2-3 years

**Implementation:**
- Install smart charging controller
- Configure priority rules
- Monitor performance

### For Medium Office Buildings (10-25 EVs)

**Recommended:** Level 2 (RL or MPC)

**Why:**
- Additional 10-20% savings vs. Simple
- Handles complexity of larger fleet
- Adapts to changing conditions
- Scalable architecture
- Payback: 3-4 years

**Implementation:**
- Deploy advanced energy management system
- Implement RL or MPC algorithm
- Integrate with building management system
- Include solar forecasting

### For Large Office Buildings (>25 EVs)

**Recommended:** Level 2 or 3 (RL with optional V2G)

**Why:**
- Maximum savings potential
- Scale justifies infrastructure investment
- V2G becomes economically attractive
- Potential for grid services revenue
- Payback: 3-5 years

**Implementation:**
- Comprehensive smart charging platform
- RL-based optimization
- V2G capability (if fleet is company-owned)
- Integration with utility programs
- Advanced monitoring and analytics

---

## Challenges and Future Work

### Technical Challenges

1. **Forecasting Uncertainty:**
   - Solar production depends on weather
   - Building consumption varies with occupancy
   - EV arrivals may be unpredictable
   - **Future work:** Stochastic optimization, robust policies

2. **Computational Complexity:**
   - Optimization time increases with fleet size
   - Real-time requirements
   - **Future work:** Distributed algorithms, edge computing

3. **Communication Infrastructure:**
   - Reliable EV-charger communication needed
   - Cybersecurity concerns
   - **Future work:** Secure protocols, standards compliance

### Economic Challenges

1. **Infrastructure Investment:**
   - High upfront costs (especially V2G)
   - Long payback periods
   - **Future work:** Shared infrastructure models, leasing options

2. **Market Structure:**
   - Not all regions have dynamic pricing
   - V2G compensation mechanisms still developing
   - **Future work:** Policy advocacy, pilot programs

### User Acceptance Challenges

1. **Battery Degradation Concerns:**
   - Users worry about V2G impact on battery life
   - Lack of clear data
   - **Future work:** Degradation studies, insurance products

2. **Mobility Anxiety:**
   - Trust in automated systems
   - Fear of insufficient charge
   - **Future work:** User interface design, education

### Research Limitations

1. **Perfect Forecasting:** Assumed perfect knowledge of future conditions
2. **Single Day:** No multi-day or seasonal patterns
3. **No Degradation:** Simplified battery model
4. **Deterministic:** Fixed arrival/departure times
5. **Homogeneous Fleet:** All EVs identical
6. **Single Location:** One climate and building type

### Future Research Priorities

**Short-term (1-2 years):**
1. Uncertainty quantification and robust optimization
2. Battery degradation modeling and V2G impact
3. Real-world pilot deployments and validation
4. User behavior and acceptance studies

**Medium-term (2-5 years):**
1. Multi-day and seasonal analysis
2. Heterogeneous fleet management
3. Machine learning-based forecasting
4. Integration with building management systems

**Long-term (5+ years):**
1. Multi-building coordination (district-level)
2. Grid services and demand response markets
3. Smart city infrastructure integration
4. Advanced AI techniques (deep RL, multi-agent systems)

---

## Impact and Significance

### Environmental Impact

- **Carbon Reduction:** Increased renewable utilization reduces emissions
- **Grid Decarbonization:** Flexible EV loads enable higher renewable penetration
- **Sustainability:** Near-zero-carbon charging during solar peak hours

**Estimated CO₂ Reduction:** 2-5 tons per year for 15-vehicle fleet

### Economic Impact

- **Cost Savings:** 30-60% reduction in EV charging costs
- **Infrastructure Deferral:** Reduces need for grid upgrades (saves billions at scale)
- **New Revenue Streams:** V2G enables EV owners to earn income
- **Business Models:** Charging-as-a-service, energy-as-a-service

### Social Impact

- **Workplace Benefits:** Attractive employee amenity
- **Energy Equity:** Charging access for apartment dwellers
- **Grid Resilience:** Distributed energy resources improve reliability
- **Technology Adoption:** Demonstrates practical AI in energy sector

---

## Thesis Structure

### Chapter 1: Introduction (15-20 pages)
- Background and motivation
- Smart charging levels overview
- Comprehensive literature review (30-50 citations)
- Research objectives and questions

### Chapter 2: Methodology (25-30 pages)
- Mathematical models for all system components
- Detailed algorithm descriptions
- Equations, pseudocode, and explanations
- Assumptions and limitations

### Chapter 3: Case Study (15-20 pages)
- Office building characteristics and data sources
- Solar PV system (PVGIS data)
- EV fleet scenario (mobility patterns)
- Grid parameters (pricing, capacity)
- Simulation configuration

### Chapter 4: Results (25-30 pages)
- Economic performance comparison
- Energy metrics (grid, solar, V2G)
- Operational performance (SoC, constraints)
- Algorithm comparison and insights
- Sensitivity analysis
- Comprehensive visualizations

### Chapter 5: Conclusions (10-15 pages)
- Summary of findings
- Practical recommendations (by fleet size)
- Challenges and limitations
- Future research directions
- Broader implications

### Appendices (10-15 pages)
- Appendix A: Code implementation details
- Appendix B: Complete data tables

**Total:** 110-150 pages

---

## Key Messages

### For Building Managers

> "Smart EV charging can reduce your electricity costs by 30-60% while supporting employee EV adoption and sustainability goals. Start with simple rule-based systems (Level 1) for immediate benefits, then upgrade to advanced optimization (Level 2) as your fleet grows."

### For Policy Makers

> "Smart charging infrastructure is essential for EV adoption and grid stability. Policies should incentivize workplace charging, support V2G development, and promote renewable integration. The technology is proven - we need supportive regulations."

### For Researchers

> "This thesis demonstrates that practical smart charging systems work. Future research should focus on uncertainty handling, battery degradation, real-world validation, and scaling to district-level coordination."

### For EV Owners

> "Smart charging saves money without compromising your mobility needs. Your EV can charge intelligently during cheap, solar-rich hours and potentially earn revenue through V2G - all while ensuring you have enough charge for your commute."

---

## Unique Selling Points

What makes this thesis stand out:

1. **Comprehensive Scope:** 4 intelligence levels, 6+ algorithms, 2 scenarios
2. **Practical Focus:** Real data, realistic constraints, actionable recommendations
3. **Implementation:** Complete working code (reproducible research)
4. **Multi-Objective:** Economic, environmental, and operational metrics
5. **Balanced Perspective:** Honest about limitations and challenges
6. **Future-Oriented:** Clear roadmap for continued research

---

## Success Metrics for Thesis

### Academic Quality
- Clear research questions and objectives
- Rigorous methodology
- Comprehensive literature review (30-50 papers)
- Valid and reproducible results
- Critical analysis and discussion

### Technical Quality
- Correct mathematical formulations
- Working implementation (tested code)
- Proper validation and verification
- Appropriate use of algorithms

### Presentation Quality
- Clear and logical structure
- High-quality figures and tables
- Professional formatting
- Minimal errors (typos, grammar)
- Consistent notation and style

### Practical Value
- Actionable recommendations
- Real-world applicability
- Cost-benefit analysis
- Implementation guidance

---

## Timeline Summary

| Week | Focus | Deliverable |
|------|-------|-------------|
| 1-2 | Data collection & analysis | All simulation results, figures |
| 2-3 | Literature review | 30-50 papers, references.bib |
| 3 | Methodology writing | Chapter 2 complete |
| 4 | Results writing | Chapter 4 complete |
| 5 | Introduction & case study | Chapters 1 & 3 complete |
| 6 | Conclusions & appendices | Chapters 5, A, B complete |
| 7-8 | Revision & finalization | Final thesis PDF |

**Total Time:** 8 weeks (assuming full-time work)

---

## Final Thoughts

This thesis addresses a timely and important problem: how to intelligently manage EV charging in office buildings to minimize costs, maximize renewable energy use, and support the transition to sustainable transportation.

The multi-level framework provides a clear progression from simple to sophisticated approaches, allowing practitioners to choose the appropriate level of intelligence based on their specific context and constraints.

The comprehensive comparison of multiple optimization algorithms fills a gap in the literature and provides valuable insights for both researchers and practitioners.

Most importantly, the thesis demonstrates that smart EV charging is not just theoretically interesting - it's practically viable, economically attractive, and ready for real-world deployment.

**The question is no longer "Can we do smart EV charging?" but rather "Which level of intelligence should we implement?"**

This thesis provides the answer.

---

## Quick Reference: Key Numbers to Remember

- **Fleet:** 15 EVs × 100 kWh = 1,500 kWh total capacity
- **Solar:** 150 m² × 20% = 30 kW peak power
- **Grid:** 80 kW capacity limit
- **Charging:** 22 kW per EV (Level 2)
- **Parking:** 7-14 hours per day
- **Savings:** 30-60% vs. uncontrolled charging
- **V2G Benefit:** €3-8 per day additional
- **Annual Savings:** €2,500-7,500 (depending on level)
- **Payback:** 2-5 years

---

**Good luck with your thesis!** 🎓⚡🌞
