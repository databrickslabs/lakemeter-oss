# 📊 Google Sheet Setup for Beta Testing

## Quick Setup Instructions

### Step 1: Create New Google Sheet
1. Go to https://sheets.google.com
2. Click "Blank" to create new spreadsheet
3. Name it: "PromptSizer Beta Testing - [Your Team]"

### Step 2: Create 4 Tabs

Rename the default tabs and create 4 sheets:
1. **User Scenarios**
2. **Feature Testing**
3. **Issues Found**
4. **Overall Feedback**

---

## Tab 1: User Scenarios

**Headers (Row 1):**
```
Tester Name | Scenario | Tried? | Worked? | Cost Accurate? | Comments
```

**Pre-fill scenarios (starting Row 2):**

| Scenario |
|----------|
| Data Ingestion - Ingest from Salesforce/S3 daily |
| ETL Jobs - Process 100GB of data nightly |
| SQL Analytics - 50 analysts querying dashboards |
| ML Training - Train model on 1TB dataset weekly |
| Real-time Streaming - Process Kafka streams 24/7 |
| Interactive Notebooks - 10 data scientists exploring data |
| DLT Pipeline - Continuous data transformation |
| Model Serving - Deploy ML model with GPU |
| Vector Search - Semantic search on documents |
| Your Own Scenario 1 |
| Your Own Scenario 2 |

**Format:**
- Add data validation for "Tried?" and "Worked?" columns: ☐ / ✓
- Or use: Yes / No

---

## Tab 2: Feature Testing

**Headers (Row 1):**
```
Tester Name | Feature | Tried? | Worked? | Rating (1-5) | Comments
```

**Pre-fill features (starting Row 2):**

| Feature |
|---------|
| AI Understanding - Did AI understand your workload description? |
| SKU Recommendations - Are recommended SKUs correct? |
| Instance Types - Are instance recommendations reasonable? |
| Cost Accuracy - Do costs match your experience/knowledge? |
| Manual Edits - Can you edit configurations after AI suggests? |
| Export to CSV - Does CSV export work? |
| Dark Mode - Does it work? |
| Multiple Workloads - Can you describe multiple workloads at once? |
| Configuration Details - Are DBU calculations shown clearly? |

**Format:**
- Rating column: Data validation 1, 2, 3, 4, 5
- Add conditional formatting:
  - 5 = Green
  - 4 = Light green
  - 3 = Yellow
  - 2 = Orange
  - 1 = Red

---

## Tab 3: Issues Found

**Headers (Row 1):**
```
Date | Tester Name | What You Did | What Went Wrong | What You Expected | Severity | Status
```

**Add one example row:**
```
2024-12-18 | Example User | Described ETL workload | AI recommended serverless but Classic would be better | AI should suggest Classic for batch ETL | Medium | Open
```

**Format:**
- Severity: Data validation dropdown
  - Critical
  - High
  - Medium
  - Low
- Status: Data validation dropdown
  - Open
  - In Progress
  - Fixed
  - Won't Fix

**Conditional formatting for Severity:**
- Critical = Red background
- High = Orange background
- Medium = Yellow background
- Low = Light gray background

---

## Tab 4: Overall Feedback

**Headers (Row 1):**
```
Tester Name | Question | Rating (1-5) | Comments/Suggestions
```

**Pre-fill questions (starting Row 2):**

| Question |
|----------|
| Easy to Use - Is it intuitive? |
| AI Quality - Are recommendations good? |
| Cost Accuracy - Do costs seem right? |
| Would You Use It? - Would you use this with customers? |
| Overall Experience |
| What worked best? |
| What needs improvement? |
| Missing features you'd want? |

**Format:**
- Rating column: Data validation 1, 2, 3, 4, 5
- Same conditional formatting as Feature Testing tab

---

## Step 3: Share Settings

1. Click "Share" button (top right)
2. Set permissions:
   - **Option A (Recommended):** "Anyone with the link can EDIT"
   - **Option B:** Add specific team member emails with "Editor" access
3. Copy the sharing link

---

## Step 4: Formatting Tips

### Make it pretty:
1. **Freeze first row:** View → Freeze → 1 row
2. **Bold headers:** Select row 1 → Bold → Center align
3. **Add background color to headers:** Light blue (#4A86E8)
4. **Set column widths:**
   - Tester Name: 150px
   - Scenario/Feature/Question: 400px
   - Comments: 300px
   - Other columns: Auto-fit

### Add instructions at the top:
1. Insert 2 rows at the very top
2. Merge cells across all columns
3. Add text:
```
PromptSizer Beta Testing - INSTRUCTIONS: Fill in your name, test scenarios, and provide feedback. 
Testing Guide: [paste Google Doc link]
```
4. Make it stand out: Bold, larger font, background color

---

## Example Google Sheet Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ PromptSizer Beta Testing - Instructions: [link]                │
│ App URL: [app url]                                             │
├─────────────────────────────────────────────────────────────────┤
│ Tab 1: User Scenarios                                           │
│ ┌────────┬──────────┬────────┬────────┬──────────┬──────────┐  │
│ │ Tester │ Scenario │ Tried? │ Worked?│ Accurate?│ Comments │  │
│ ├────────┼──────────┼────────┼────────┼──────────┼──────────┤  │
│ │        │ Data...  │   ✓    │   ✓    │   Yes    │ Good!    │  │
│ └────────┴──────────┴────────┴────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 5: Create Companion Google Doc

1. Create a new Google Doc
2. Copy-paste content from `PromptSizer_Beta_Testing_Guide_GoogleDocs.txt`
3. Format nicely:
   - Make headers larger and bold
   - Add colors to section headers
   - Use bullet lists
4. Share with "Anyone with link can VIEW"
5. Add link to Google Doc in the Google Sheet instructions

---

## Final Checklist

- [ ] Google Sheet created with 4 tabs
- [ ] All headers and pre-filled content added
- [ ] Data validation added (dropdowns for Yes/No, ratings, severity)
- [ ] Conditional formatting applied (colors for ratings/severity)
- [ ] Sheet shared with edit permissions
- [ ] Google Doc created with testing guide
- [ ] Google Doc link added to Sheet
- [ ] App URL added to Sheet
- [ ] Sharing links copied for email

---

## Email Template for Beta Testers

```
Subject: PromptSizer Beta Testing - Let's Go! 🚀

Hi team,

We're ready for beta testing! Here's everything you need:

📊 GOOGLE SHEET (fill this in as you test):
[Paste Google Sheet link]

📖 TESTING GUIDE (read this first):
[Paste Google Doc link]

🔗 PROMPTSIZER APP:
[Paste app URL]

⏱️ TIME: 20-30 minutes

📝 WHAT TO DO:
1. Read the testing guide (5 min)
2. Open PromptSizer and test 3+ scenarios (15 min)
3. Fill in your results in the Google Sheet (10 min)

🙏 Your feedback will directly shape the final product!

Questions? Reply to this email or ping us on Slack.

Thanks!
[Your name]
```

---

## Quick Import Option

**If you want to skip manual setup:**

1. Import CSV files into Google Sheets:
   - File → Import → Upload
   - Select the 4 CSV files from beta_test_templates/
   - Import each as a separate tab

2. Adjust formatting as needed

3. Add instruction rows at top

4. Share and send!

---

**That's it! Your beta testing Google Sheet is ready.** 🎉

