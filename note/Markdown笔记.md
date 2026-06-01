# Markdown / LaTeX 常用公式速查表（Obsidian 可直接渲染）

## 1. 基础运算

|含义|写法|效果|
|---|---|---|
|加|`+`|$a+b$|
|减|`-`|$a-b$|
|乘|`\times`|$a \times b$|
|点乘|`\cdot`|$a \cdot b$|
|除|`\div`|$a \div b$|
|分数|`\frac{a}{b}`|$\frac{a}{b}$|
|幂|`a^2`|$a^2$|
|下标|`a_i`|$a_i$|
|根号|`\sqrt{x}`|$\sqrt{x}$|
|n次根号|`\sqrt[n]{x}`|$\sqrt[n]{x}$|

---

# 2. 比较符号

|含义|写法|效果|
|---|---|---|
|等于|`=`|$a=b$|
|不等于|`\neq`|$a \neq b$|
|小于|`<`|$a<b$|
|大于|`>`|$a>b$|
|小于等于|`\le`|$a \le b$|
|大于等于|`\ge`|$a \ge b$|
|约等于|`\approx`|$a \approx b$|
|恒等于|`\equiv`|$a \equiv b$|

---

# 3. 最大值最小值

|含义|写法|效果|
|---|---|---|
|最大值|`\max`|$\max(a,b)$|
|最小值|`\min`|$\min(a,b)$|
|最大值点|`\arg\max`|$\arg\max_x f(x)$|
|最小值点|`\arg\min`|$\arg\min_x f(x)$|
|正无穷|`\infty`|$\infty$|
|负无穷|`-\infty`|$-\infty$|

---

# 4. 集合论

|含义|写法|效果|
|---|---|---|
|属于|`\in`|$a \in A$|
|不属于|`\notin`|$a \notin A$|
|包含|`\subset`|$A \subset B$|
|真包含|`\subsetneq`|$A \subsetneq B$|
|并集|`\cup`|$A \cup B$|
|交集|`\cap`|$A \cap B$|
|空集|`\emptyset`|$\emptyset$|
|实数集|`\mathbb{R}`|$\mathbb{R}$|
|整数集|`\mathbb{Z}`|$\mathbb{Z}$|

---

# 5. 求和与连乘

|含义|写法|效果|
|---|---|---|
|求和|`\sum`|$\sum$|
|连乘|`\prod`|$\prod$|
|极限|`\lim`|$\lim$|
|积分|`\int`|$\int$|

例子：

```latex
$\sum_{i=1}^{n} i$
```

效果：

$\sum_{i=1}^{n} i$

---

# 6. 逻辑符号

|含义|写法|效果|
|---|---|---|
|且|`\land`|$A \land B$|
|或|`\lor`|$A \lor B$|
|非|`\neg`|$\neg A$|
|推出|`\Rightarrow`|$A \Rightarrow B$|
|等价|`\Leftrightarrow`|$A \Leftrightarrow B$|
|任意|`\forall`|$\forall x$|
|存在|`\exists`|$\exists x$|

---

# 7. 箭头

|含义|写法|效果|
|---|---|---|
|右箭头|`\to`|$a \to b$|
|长右箭头|`\longrightarrow`|$a \longrightarrow b$|
|双向箭头|`\leftrightarrow`|$a \leftrightarrow b$|
|映射|`\mapsto`|$x \mapsto y$|

---

# 8. 向量与矩阵

|含义|写法|效果|
|---|---|---|
|向量|`\vec{v}`|$\vec{v}$|
|粗体|`\mathbf{x}`|$\mathbf{x}$|
|转置|`A^T`|$A^T$|

矩阵例子：

```latex
$$
\begin{bmatrix}
1 & 2 \\
3 & 4
\end{bmatrix}
$$
```

效果：

$$  
\begin{bmatrix}  
1 & 2 \  
3 & 4  
\end{bmatrix}  
$$

---

# 9. 概率统计

|含义|写法|效果|
|---|---|---|
|概率|`P(A)`|$P(A)$|
|条件概率|`P(A \mid B)`|$P(A \mid B)$|
|期望|`\mathbb{E}`|$\mathbb{E}[X]$|
|方差|`\mathrm{Var}`|$\mathrm{Var}(X)$|
|协方差|`\mathrm{Cov}`|$\mathrm{Cov}(X,Y)$|
|正态分布|`\mathcal{N}`|$\mathcal{N}(0,1)$|

---

# 10. 动态规划高频写法

| 含义     | 效果                  |
| ------ | ------------------- |
| 状态定义   | $dp[i]$             |
| 二维状态   | $dp[i][j]$          |
| 转移     | $dp[i] = \min(...)$ |
| 初始化无穷大 | $\infty$            |
| 不可达    | $dp[i] = \infty$    |

---

# 11. 行内公式与块公式

## 行内公式

```markdown
$a+b$
```

效果：

$a+b$

---

## 块级公式

```markdown
$$
a+b
$$
```

效果：

$$  
a+b  
$$

---

# 12. 动态规划经典例子

```markdown
$$
dp[i] = \min(dp[i], dp[i-coin]+1)
$$
```

效果：

$$  
dp[i] = \min(dp[i], dp[i-coin]+1)  
$$

---

```markdown
$$
dp[i][j] = dp[i-1][j] + dp[i][j-1]
$$
```

效果：

$$  
dp[i][j] = dp[i-1][j] + dp[i][j-1]  
$$

---

```markdown
$$
dp[i] = \max(dp[i-1], dp[i-2]+nums[i])
$$
```

效果：

$$  
dp[i] = \max(dp[i-1], dp[i-2]+nums[i])  
$$