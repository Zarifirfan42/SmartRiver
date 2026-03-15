# How to Update SmartRiver on GitHub

Your project is already linked to: **https://github.com/Zarifirfan42/SmartRiver.git**

## Steps to push your latest changes

### 1. Open a terminal in the project folder

```powershell
cd "c:\Users\irfan\Downloads\FYP 2526\SmartRiver"
```

### 2. Stage all changes

```powershell
git add -A
```

(This adds modified files and new files like `dataset_loader.py` and `AlertsBySeverityChart.jsx`.)

### 3. Commit with a message

```powershell
git commit -m "Refactor: dataset-driven UI, dashboard export, station filters, chart titles"
```

(Use any message you prefer.)

### 4. Push to GitHub

```powershell
git push origin main
```

If your default branch is `master` instead of `main`:

```powershell
git push origin master
```

---

## If Git asks for login

- **HTTPS:** GitHub may ask for your username and a **Personal Access Token** (not your password). Create one at: GitHub → Settings → Developer settings → Personal access tokens.
- **SSH:** If you prefer SSH, change the remote and push:
  ```powershell
  git remote set-url origin git@github.com:Zarifirfan42/SmartRiver.git
  git push origin main
  ```

## Check after pushing

Open **https://github.com/Zarifirfan42/SmartRiver** in your browser; your latest commit should appear on the default branch.
