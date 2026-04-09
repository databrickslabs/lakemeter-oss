# 📊 PromptSizer Beta Test - Simple Template

## 🎯 What You're Testing

**PromptSizer** = Describe your Databricks workload → AI recommends configuration → Get cost estimate

---

## 📝 4 Simple Sheets to Fill

### Sheet 1: User Scenarios Tested

| Scenario | Tried? | Worked? | Cost Accurate? | Comments |
|----------|--------|---------|----------------|----------|
| **Data Ingestion** - "Ingest from Salesforce daily" | | | | |
| **ETL Jobs** - "Process 100GB of data nightly" | | | | |
| **SQL Analytics** - "50 analysts querying dashboards" | | | | |
| **ML Training** - "Train model on 1TB dataset weekly" | | | | |
| **Real-time Streaming** - "Process Kafka streams 24/7" | | | | |
| **Interactive Notebooks** - "10 data scientists exploring data" | | | | |
| **Your Own Scenario** | | | | |

---

### Sheet 2: Feature Testing

| Feature | Tried? | Worked? | Rating (1-5) | Comments |
|---------|--------|---------|--------------|----------|
| **AI Understanding** - Did AI understand your workload description? | | | | |
| **SKU Recommendations** - Are recommended SKUs correct? | | | | |
| **Instance Types** - Are instance recommendations reasonable? | | | | |
| **Cost Accuracy** - Do costs match your experience/knowledge? | | | | |
| **Manual Edits** - Can you edit configurations after AI suggests? | | | | |
| **Export to CSV** - Does CSV export work? | | | | |
| **Dark Mode** - Does it work? | | | | |

---

### Sheet 3: Issues Found

| Date | Your Name | What You Did | What Went Wrong | What You Expected | Severity |
|------|-----------|--------------|-----------------|-------------------|----------|
| | | | | | |

**Severity:**
- **Critical** - Can't use the tool at all
- **High** - Feature doesn't work or gives wrong results
- **Medium** - Confusing or annoying
- **Low** - Minor issue or suggestion

---

### Sheet 4: Overall Feedback

| Question | Your Answer (1-5) | Comments/Suggestions |
|----------|-------------------|----------------------|
| **Easy to Use** - Is it intuitive? | | |
| **AI Quality** - Are recommendations good? | | |
| **Cost Accuracy** - Do costs seem right? | | |
| **Would You Use It?** - Would you use this with customers? | | |
| **Overall Experience** | | |

**Rating Scale:**
- 5 = Excellent, ready to use
- 4 = Good, minor improvements needed
- 3 = OK, needs some work
- 2 = Poor, major issues
- 1 = Unusable

---

## 🚀 How to Test (5 Steps)

### Step 1: Access the Tool
- Get the URL from the team
- Login if needed

### Step 2: Try Basic Scenarios (10-15 min)
**Test at least 3 different workload types:**

**Example 1 - Data Ingestion:**
```
Describe your workload:
"We need to ingest data from Salesforce every hour,
processing about 5GB per run"
```
→ Click "Analyze Workload"
→ Check if recommendations make sense
→ Review cost estimate

**Example 2 - SQL Analytics:**
```
"50 business analysts running SQL queries 8 hours a day,
typical queries take 30 seconds, about 200 queries per day"
```

**Example 3 - ETL Jobs:**
```
"Nightly ETL job processing 500GB of data,
takes about 2 hours to run, 6 days a week"
```

### Step 3: Test Manual Editing (5 min)
- After AI suggests configuration, try editing:
  - Change instance type
  - Change number of workers
  - Change run frequency
- See if costs update correctly

### Step 4: Test Edge Cases (5 min)
Try to break it:
- Very vague description: "I need to process data"
- Very detailed description: "..."
- Unrealistic requirements: "1 billion records per second"
- Multiple workloads in one prompt

### Step 5: Compare with Real Costs (if possible)
If you have actual Databricks costs for similar workloads:
- Compare AI-estimated costs with actual costs
- Note: ±10% difference is acceptable

---

## 💡 What We're Looking For

### Critical Issues:
- ❌ AI gives completely wrong recommendations
- ❌ Costs are wildly incorrect (>50% off)
- ❌ Tool crashes or freezes
- ❌ Can't edit configurations
- ❌ Export doesn't work

### High Value Feedback:
- 💡 "AI didn't understand X workload type"
- 💡 "Costs are off for Y scenario"
- 💡 "I wish it could do Z"
- 💡 "This part was confusing"

### Nice to Have:
- ✨ UI/UX suggestions
- ✨ Missing workload types
- ✨ Additional features you'd want

---

## 📧 Submitting Your Results

**Option 1: Fill the Google Sheet**
- [Link to shared Google Sheet - to be provided]

**Option 2: Email Spreadsheet**
- Download template CSVs
- Fill them in
- Email back to team

**Option 3: Quick Feedback**
Just answer these 5 questions:
1. What scenarios did you test?
2. What worked well?
3. What didn't work?
4. Any wildly incorrect costs?
5. Would you use this with customers? Why/why not?

---

## ❓ Quick FAQ

**Q: How accurate should costs be?**
A: Within ±10% of actual costs is great. Within ±20% is acceptable for beta.

**Q: What if I don't know Databricks costs?**
A: That's fine! Just test if AI understands your workload and recommendations seem reasonable.

**Q: How long should testing take?**
A: 20-30 minutes minimum. More is better!

**Q: What if I find bugs?**
A: Note them in Sheet 3 (Issues Found). Critical bugs - let team know immediately!

**Q: Can I test multiple times?**
A: Yes! Try different workload descriptions and see if you get consistent results.

---

## 🎯 Success Criteria

You've completed beta testing if you:
- ✅ Tested at least 3 different workload scenarios
- ✅ Tried editing AI recommendations manually
- ✅ Filled in all 4 sheets
- ✅ Noted any major issues or bugs
- ✅ Gave overall feedback (would you use it?)

---

**Time Estimate**: 20-30 minutes minimum  
**Best Testing Approach**: Try real scenarios from your field experience  
**Most Valuable**: Comparing costs with actual customer workloads

**Thank you for helping us improve PromptSizer! 🚀**

