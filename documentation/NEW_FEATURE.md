### Step 1: Start from main
```
git checkout main
git pull
```

### Step 2: Create feature branch
```
git checkout -b feature/what-feature-is
```

### Step 3: Work and commit often
```
# Make changes
git add .
git commit -m "Added feature"

# Make more changes
git add .
git commit -m "Fixed feature bug"
```

### Step 4: Push to GitHub
```
git push -u origin feature/what-feature-is
```

### Step 5: When done, merge to main
```
git checkout main
git merge feature/what-feature-is
git push
```

### Step 6: Delete feature branch
```
git branch -d feature/what-feature-is
git push origin --delete feature/what-feature-is
```


