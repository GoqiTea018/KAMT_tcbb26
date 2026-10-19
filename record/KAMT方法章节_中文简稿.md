# KAMT 方法章节：理论与公式说明（中文简稿）

本文依据 [KAMT-tcbb-short.tex 第三章](/D:/Document/KAMT-tcbb/58f56a73-306d-4889-aa82-99aae0d51265/KAMT-tcbb-short.tex:97) 的最新条件自由能、最优知识权重和知识读出公式整理。以下按英文稿的方法顺序解释各计算关系，保留其主要符号；编号用于本说明，括号中的 LaTeX 标签用于与英文稿对应。

## 建图流程与方法概述

KAMT 先将外部生物医学知识组织成任务相关的 DemRKG，再根据患者观测选择可使用的知识实体，通过条件自由能确定各实体对不同模态分支的贡献，最后将知识增强后的表征用于多模态分类。

DemRKG 的构建分为以下步骤：

1. **临床种子对齐。** 将成功匹配的临床字段映射为 PrimeKG 实体，并加入任务相关的疾病和分子核心实体，形成图谱提炼的起点。
2. **一跳关系提取与筛选。** 提取与种子相连的一跳边，依据实体类型和关系进行过滤，保留相关的邻域关系。
3. **二跳候选扩展与剪枝。** 从经过筛选的一跳邻域继续扩展，对二跳候选边进行相同过滤；按候选目标与不同来源的连接数及其 PrimeKG 全局连接度计算评分，分别为每个来源保留 Top-$k$ 候选边记录。
4. **合并形成 DemRKG。** 将保留的二跳边与经过过滤的一跳边合并，去除重复记录，得到用于关系表示学习的三元组集合。
5. **关系表征学习。** 使用 DistMult 在精炼三元组上训练实体与关系嵌入，得到实体嵌入表 $\mathbf E$，供后续患者知识序列查表使用。

患者知识激活发生在建图之后。对每个患者，临床观测经过字段对应的激活规则和实体映射，形成有效知识位置集合 $J_i$ 及知识序列 $\mathbf X_{KG}^{(i)}$。EHR、BM 和 MRI 分支分别产生 Query，知识序列经分支适配形成 Key 和 Value。相容性能量与 KL 项共同确定最优知识权重 $\alpha^*$，这些权重控制 Value 聚合，得到知识响应。知识响应与原模态表征通过残差相加和 LayerNorm 形成增强表征，再进入分支融合与分类。

完整计算路径为：

$$
\text{PrimeKG}
\longrightarrow\text{种子对齐与邻域精炼}
\longrightarrow\text{DemRKG 与关系训练嵌入}
\longrightarrow\text{患者知识序列与 }J_i
\longrightarrow\text{Query/Key/Value}
\longrightarrow\epsilon_{imj}
\longrightarrow\alpha_{im}^{*}
\longrightarrow\text{Value 读出与残差更新}
\longrightarrow\text{多模态融合与分类}.
$$

DemRKG 的作用贯穿三处：关系训练后的实体嵌入形成 Key，参与相容性能量计算；患者激活与嵌入可用性共同确定有效支持 $J_i$；实体嵌入形成 Value，提供实际注入的知识内容。MRI 提供互补的影像信息，与两组临床表征共同参与预测。

## 主要符号

| 符号 | 含义 |
| --- | --- |
| $i$ | 患者索引；批量计算时索引批次中的患者 |
| $f$ | 临床字段索引，例如某个量表项目或病史字段 |
| $m$ | 模态分支，取 EHR、BM 或 MRI |
| $j,\ell$ | 患者知识序列的位置索引 |
| $a$、$H$ | 注意力头索引、注意力头总数 |
| $L_{kg}$ | 补齐后的知识序列长度 |
| $d$ | 图谱实体与关系嵌入维度 |
| $d_k$ | 每个注意力头的 Key 维度，也与该头的 Query 维度一致 |
| $\mathbf h_{im}$ | 患者 $i$ 在分支 $m$ 的编码表征 |
| $\alpha_{im}^{*}$ | 分支 $m$ 在患者知识位置上的最优权重分布 |
| $\mathbf z_{im}^{kg}$ | 多头知识读出得到的知识响应向量 |
| $B$、$C$ | 分类训练的批次大小、类别数 |

图谱中的三元组头实体 $h$ 与模态向量 $\mathbf h_{im}$ 属于不同符号用法：前者是实体标识，后者是患者特征向量。$L(w)$ 是候选来源计数，$L_{kg}$ 是知识序列长度，$\mathcal L$ 是损失函数。

## 3.1 DemRKG 的提炼与关系表征

### 3.1.1 临床种子集合

设 PrimeKG 为 $\mathcal G_0=(\mathcal V_0,\mathcal R_0,\mathcal T_0)$，其中 $\mathcal V_0$、$\mathcal R_0$ 和 $\mathcal T_0$ 分别是原图的实体、关系类型和三元组集合。将成功匹配的临床字段 $\mathcal F$ 通过映射 $M:\mathcal F\rightarrow\mathcal V_0$ 转换为临床种子，再加入核心种子：

$$
\mathcal S
=\mathcal S_{\mathrm{clinical}}
\cup\mathcal S_{\mathrm{core}}.
\tag{1}
$$

对应英文稿：`eq:seed_set`。

$\mathcal S_{\mathrm{clinical}}$ 是由临床字段映射得到的实体集合，$\mathcal S_{\mathrm{core}}$ 是任务相关的疾病和分子实体集合，$\cup$ 表示并集。多个字段可以映射到同一个医学实体，集合操作将重复实体合并。

式 (1) 确定整个任务的图谱提炼起点。临床种子建立观测字段与医学概念的联系，核心种子补充关系扩展所需的疾病和分子知识。后续患者激活再根据个人观测确定具体使用哪些实体。

### 3.1.2 候选目标的特异性评分

在一跳筛选和二跳候选扩展之后，对候选目标节点 $w$ 定义评分：

$$
Score(w)=\frac{L(w)}{\ln(1+G(w))}.
\tag{2}
$$

对应英文稿：`eq:spec-score`。

$L(w)$ 统计二跳候选边中连接到 $w$ 的不同来源节点数；$G(w)$ 统计 $w$ 在 PrimeKG 任一端点出现的记录次数；$\ln$ 是自然对数。分子反映目标与多个候选来源的连接，分母对全局高连接度施加惩罚。相同全局连接度下，连接更多不同来源的目标得分更高；相同来源计数下，全局连接度较低的目标得分更高。

对数使连接度惩罚随全局计数增长而逐渐放缓。评分所使用的全局计数来自 PrimeKG，候选来源计数来自经过过滤的扩展关系，两者分别提供原图连接度与当前候选邻域的信息。

根据目标评分，分别为每个来源保留 Top-$k$ 候选边记录。随后将这些记录与经过过滤的一跳边合并、去重，得到精炼三元组 $\mathcal T$。因此，评分影响的是用于关系表示学习的图结构；其影响随后通过训练后的实体嵌入传递到知识加权与读出。

### 3.1.3 DistMult 三元组评分

在 DemRKG 的三元组上训练实体和关系嵌入。DistMult 的评分为：

$$
f(h,r,t)
=\langle\mathbf e_h,\mathbf r_r,\mathbf e_t\rangle
=\sum_{s=1}^{d}e_{h,s}\,r_{r,s}\,e_{t,s}.
\tag{3}
$$

对应英文稿：Relation-Trained Entity Representations 中的 DistMult 定义。求和形式用于展开原文的三线性内积。

$h$、$r$、$t$ 分别是头实体、关系类型和尾实体；$\mathbf e_h$、$\mathbf e_t$ 是两个实体的嵌入，$\mathbf r_r$ 是关系嵌入；$s$ 索引嵌入维度。三线性内积将三组向量逐维相乘后求和，得到三元组的相容性分数。

训练目标推动观测三元组的评分高于随机替换得到的三元组。实体向量由此受到其参与的关系三元组共同影响，形成后续知识读取所使用的关系表征。

### 3.1.4 间隔排序损失

对每个正三元组 $(h,r,t)$ 随机替换一次尾实体，得到 $(h,r,t')$，训练目标为：

$$
\mathcal L
=\frac{1}{|\mathcal B|}
\sum_{(h,r,t)\in\mathcal B}
\max\left(0,\gamma-f(h,r,t)+f(h,r,t')\right).
\tag{4}
$$

对应英文稿：`eq:margin_loss`。

$\mathcal B$ 是图谱预训练的三元组批次，$|\mathcal B|$ 是其中的正三元组数；$t'$ 是替换尾实体；$\gamma=1.0$ 是正、负评分之间期望达到的间隔。这里的 $\mathcal B$ 与分类训练的批次大小 $B$ 分别用于两个训练阶段。

当 $f(h,r,t)-f(h,r,t')\geq\gamma$ 时，该对样本的损失为零；当评分差小于间隔时，损失推动正评分提高或负评分降低。式 (4) 通过批次平均学习图谱实体与关系参数。

### 3.1.5 实体表和关系表

训练得到：

$$
\mathbf E\in\mathbb R^{|\mathcal V|\times d},
\qquad
\mathbf R\in\mathbb R^{|\mathcal R|\times d}.
\tag{5}
$$

对应英文稿：Relation-Trained Entity Representations 中的嵌入表定义。

$\mathcal V$ 和 $\mathcal R$ 分别是精炼图的实体集合与关系类型集合。$\mathbf E$ 的每一行对应一个实体向量，$\mathbf R$ 的每一行对应一种关系向量。关系嵌入参与三元组训练，患者知识序列通过索引实体表 $\mathbf E$ 获得向量。

图扩展得到的关系和实体共同参与预训练。即使患者序列主要由临床激活实体组成，这些实体的嵌入也已在精炼图关系中学习，其关系信息随后进入 Key 和 Value。

## 3.2 多模态编码与患者知识激活

### 3.2.1 临床特征分组

将清洗后的诊断表格特征分为 EHR 与 BM 两组：

$$
\mathcal M_{\mathrm{EHR}},\mathcal M_{\mathrm{BM}}
=f_{\mathrm{split}}(\mathcal D_{\mathrm{clean}}).
\tag{6}
$$

对应英文稿：`eq:modality_split`。

$\mathcal D_{\mathrm{clean}}$ 是清洗后的诊断数据，$f_{\mathrm{split}}$ 是按字段类型分组的操作，$\mathcal M_{\mathrm{EHR}}$ 与 $\mathcal M_{\mathrm{BM}}$ 是两组特征。这里的 split 表示特征分组。

EHR 包含相对稳定的人口学、病史和遗传属性；BM 包含反映认知、行为和运动功能变化的临床量表。两组特征分别编码，使其能够以不同的分支表征查询同一患者知识序列。

### 3.2.2 两层 MLP 编码

第一层计算：

$$
\mathbf h
=\mathrm{ReLU}\left(\mathrm{BN}(\mathbf W_1\mathbf x+\mathbf b_1)\right).
\tag{7}
$$

对应英文稿：`eq:MLP_1`。

$\mathbf x$ 是某一临床分支的输入特征，$\mathbf W_1$ 和 $\mathbf b_1$ 是第一层权重与偏置，BN 表示批归一化，ReLU 表示非线性激活。输出 $\mathbf h$ 是该编码器的第一层中间表征。

第二层计算：

$$
\mathbf z
=\mathrm{ReLU}\left(
\mathrm{BN}\left(\mathbf W_2\mathrm{Dropout}(\mathbf h)+\mathbf b_2\right)
\right).
\tag{8}
$$

对应英文稿：`eq:MLP_2`。

$\mathbf W_2$ 和 $\mathbf b_2$ 是第二层参数；Dropout 在训练中随机丢弃部分中间特征。第二层得到分支编码输出 $\mathbf z$。EHR 与 BM 使用各自的编码器参数；后续统一将患者 $i$ 的分支输出记为 $\mathbf h_{im}$。

式 (7) 的 $\mathbf h$ 是编码器中间量，后续的 $\mathbf h_{im}$ 则是完整编码器的输出。两层计算将临床特征转换为知识 Query 所需要的模态表征。

### 3.2.3 患者知识激活与查表

对患者临床字段应用激活规则，生成知识实体序列并查找嵌入：

$$
\begin{aligned}
a_{if}&=\mathcal A_f(x_{if};\eta_f^{\mathrm{train}}),\\
\nu_i&=\operatorname{Seq}_{L_{kg}}\bigl((M(f))_{f:a_{if}=1}\bigr),\\
J_i&=\{j\in I_i:\nu_i(j)\in\mathcal V\},\\
\mathbf X_{KG}^{(i)}[j]&=\mathbf E_{\nu_i(j)},\qquad j\in J_i.
\end{aligned}
\tag{9}
$$

对应英文稿：`eq:patient_activation`。

第一行决定字段是否激活。$x_{if}$ 是患者 $i$ 的字段 $f$ 观测值，$\mathcal A_f$ 是该字段的二值规则，$a_{if}\in\{0,1\}$ 是激活结果。规则使用训练集参考统计量 $\eta_f^{\mathrm{train}}$ 或预设阈值；参考统计量估计后固定，用于各数据划分中的患者。

第二行将激活且具有映射的字段转换为实体。$M(f)$ 沿用建图阶段的临床映射，$\operatorname{Seq}_{L_{kg}}$ 完成设定的去重、截断与补齐，$\nu_i(j)$ 表示第 $j$ 个位置的实体或补齐标记。

第三行确定有效位置。$I_i=\{1,\ldots,L_{kg}\}$ 是全部位置索引，$J_i$ 保留能够在精炼图实体表中查到嵌入的位置。因此，$J_i$ 是位置集合，$\nu_i(j)$ 才是对应的实体标识。

第四行执行查表。$\mathbf E_{\nu_i(j)}$ 是对应实体的嵌入，组成 $\mathbf X_{KG}^{(i)}\in\mathbb R^{L_{kg}\times d}$。$J_i$ 之外的位置填充零向量，并由掩码 $\mathbf m_i$ 排除。

同一任务的患者共享实体表，但个人观测产生不同的知识支持与序列。若 $J_i=\varnothing$，序列保持零填充，开放首个位置作为零输入占位，继续使用相同的适配、读出与残差更新流程。有效医学实体支持仍记为 $J_i$，占位用于空知识输入的计算处理。

### 3.2.4 MRI 编码

$$
Z_{img}
=\phi_{\mathrm{img}}\left(\operatorname{CenterCrop}(I)\right).
\tag{10}
$$

对应英文稿：`eq:mri_projection`。

$I$ 是 MRI 体数据，$\operatorname{CenterCrop}$ 是中心裁剪，$\phi_{\mathrm{img}}$ 是包含卷积、池化和全连接层的 3D-CNN，$Z_{img}$ 是其输出。MRI 分支将该输出映射为 $\mathbf h_{i,\mathrm{MRI}}$，用于知识查询和后续融合。

式 (10) 提供互补影像表征。EHR、BM 和 MRI 的编码共同为后续三分支知识读取提供患者侧输入。

## 3.3 条件自由能、知识读出与多模态预测

### 3.3.1 Query、Key 与 Value

对患者 $i$、分支 $m\in\{\mathrm{EHR},\mathrm{BM},\mathrm{MRI}\}$，单个注意力头的计算为：

$$
\begin{aligned}
g_{imj}&=A_m(\mathbf X_{KG}^{(i)}[j]),\\
q_{im}&=W_m^Q\mathbf h_{im}+b_m^Q,\\
k_{imj}&=W_m^Kg_{imj}+b_m^K,\\
v_{imj}&=W_m^Vg_{imj}+b_m^V.
\end{aligned}
\tag{11}
$$

对应英文稿：`eq:knowledge_qkv`。

$A_m$ 是分支专属的知识适配器，$g_{imj}$ 是适配后的知识向量；$W_m^Q,W_m^K,W_m^V$ 及其偏置是 Query、Key、Value 的学习型映射参数。

$q_{im}$ 来自患者分支表征，表达当前分支的查询；$k_{imj}$ 来自第 $j$ 个知识位置，用于计算相容性；$v_{imj}$ 提供该位置被读出时的内容。Key 和 Value 使用同一次适配输出，经过不同映射承担评分与读出两个角色。

三分支查询同一患者知识序列，但具有各自的适配器与注意力映射，因此同一实体能够在不同分支中获得不同的权重与读出表示。式 (11) 按单头书写；多头读出时用上标 $(a)$ 区分各头。

### 3.3.2 相容性能量

$$
\epsilon_{imj}
=-\frac{q_{im}^{\mathsf T}k_{imj}}{\sqrt{d_k}}.
\tag{12}
$$

对应英文稿：`eq:energy_min` 前的能量定义。

$q_{im}^{\mathsf T}k_{imj}$ 是 Query 与 Key 的内积，$d_k$ 是该头的 Key 维度，$\sqrt{d_k}$ 对内积尺度进行归一化。Query 与 Key 的相容性越高，负内积定义的能量越低。

这里的能量是学习表示之间的相容性指标。DemRKG 的关系训练嵌入通过 Key 参与其计算，患者分支表征通过 Query 参与其计算。

### 3.3.3 条件自由能目标

对非空有效支持 $J_i$，可行知识权重满足：

$$
\Delta(J_i)
=\left\{\alpha\in\mathbb R_{\geq0}^{L_{kg}}:
\sum_{j=1}^{L_{kg}}\alpha_j=1,
\ \alpha_j=0\ (j\notin J_i)\right\}.
$$

其中 $\mathbb R_{\geq0}$ 明确表示非负数，与英文稿可行域中的 $\mathbb R_+$ 含义一致。$\alpha$ 是全部知识位置上的概率向量；有效位置获得权重，无效位置权重为零，总权重为 1。在有效支持上定义均匀参考分布 $u_i(j)=1/|J_i|$，并在支持之外延拓为零。

最优知识权重由条件自由能决定：

$$
\boxed{
\begin{aligned}
\alpha_{im}^{*}
&=\arg\min_{\alpha\in\Delta(J_i)}\mathcal F_{im}(\alpha),\\
\mathcal F_{im}(\alpha)
&=-\sum_{j\in J_i}\alpha_j
\frac{q_{im}^{\mathsf T}k_{imj}}{\sqrt{d_k}}
+D_{\mathrm{KL}}(\alpha\Vert u_i).
\end{aligned}}
\tag{13}
$$

对应英文稿：`eq:energy_min`。

$\mathcal F_{im}$ 是患者 $i$、分支 $m$ 的条件自由能；$\arg\min$ 返回使目标最小的权重分布；$\alpha_{im}^{*}$ 中的星号标记这一最优分布。

第一项等于 $\sum_{j\in J_i}\alpha_j\epsilon_{imj}$，是知识分布下的期望相容性能量，使分配倾向于与当前 Query 更相容的知识位置。第二项为 KL 散度：

$$
D_{\mathrm{KL}}(\alpha\Vert u_i)
=\sum_{j\in J_i}\alpha_j\log\frac{\alpha_j}{u_i(j)}
=\sum_{j\in J_i}\alpha_j\log\alpha_j+\log|J_i|.
$$

最后一个等式使用了均匀参考分布与权重和为 1 的性质。约定零权重对应的项为零。$-\sum_j\alpha_j\log\alpha_j$ 是分布熵，因此 KL 项等于负熵加常数，对偏离均匀分布的分配赋予代价。

两个部分共同决定知识权重：能量项反映模态与知识的相容性，KL 项调节权重分布的集中程度。称为“条件”自由能，是因为每次分配以当前患者、分支、Query、Key 和有效支持为条件。

这也说明能量约束的具体位置：患者激活规定允许参与分配的知识支持，条件自由能规定该支持上的权重分配准则。分配结果通过 Value 读出进入特征更新。

### 3.3.4 闭式解及唯一最优性

固定本次计算的 Query、Key 和非空 $J_i$，有效位置上的能量为有限值时，式 (13) 的解为：

$$
\begin{aligned}
\alpha_{imj}^{*}
&=\begin{cases}
\displaystyle\frac{e^{-\epsilon_{imj}}}
{\sum_{\ell\in J_i}e^{-\epsilon_{im\ell}}},&j\in J_i,\\[6pt]
0,&j\notin J_i,
\end{cases}\\
\mathcal F_{im}(\alpha)-\mathcal F_{im}(\alpha^*)
&=D_{\mathrm{KL}}(\alpha\Vert\alpha^*)\geq0.
\end{aligned}
\tag{14}
$$

对应英文稿：`eq:knowledge_optimum`。

$\ell$ 是归一化求和的位置索引，分母将有效位置上的指数能量归一化。较低能量对应更大的指数权重，无效位置的权重为零。

第二行表示任何可行分布相对于最优分布的目标差，恰好等于二者的 KL 散度。KL 非负，且为零时两个分布相同，因此 $\alpha^*$ 是唯一最优分布。

**推导。** 令 $n_i=|J_i|$、$Z_{im}=\sum_{j\in J_i}e^{-\epsilon_{imj}}$。这里 $n_i$ 是有效位置数，$Z_{im}$ 是能量归一化常数，与 MRI 输出 $Z_{img}$ 分别使用。由闭式解有：

$$
\log\alpha_{imj}^{*}=-\epsilon_{imj}-\log Z_{im}.
$$

将其代入 KL 散度，并使用 $\sum_j\alpha_j=1$，得到：

$$
\begin{aligned}
D_{\mathrm{KL}}(\alpha\Vert\alpha^*)
&=\sum_{j\in J_i}\alpha_j\log\alpha_j
+\sum_{j\in J_i}\alpha_j\epsilon_{imj}
+\log Z_{im},\\
\mathcal F_{im}(\alpha)
&=D_{\mathrm{KL}}(\alpha\Vert\alpha^*)
+\log n_i-\log Z_{im}.
\end{aligned}
$$

当 $\alpha=\alpha^*$ 时，KL 项为零，最小自由能为 $\log n_i-\log Z_{im}$；两式相减即得到式 (14) 的最优性恒等式。该推导将自由能目标、闭式解和唯一性连接起来。

### 3.3.5 Masked softmax 表达

将式 (12) 的能量定义代入式 (14)：

$$
\alpha_{im}^{*}
=\operatorname{softmax}\left(
\frac{K_{im}^{\mathsf T}q_{im}}{\sqrt{d_k}}+M_i
\right).
\tag{15}
$$

对应英文稿：`eq:knowledge_weights`。

$K_{im}=[k_{im1},\ldots,k_{imL_{kg}}]$ 将各知识 Key 按列排列，维度为 $d_k\times L_{kg}$；$K_{im}^{\mathsf T}q_{im}$ 是全部位置的相容性分数向量。$M_i(j)$ 在有效位置取 0，在其他位置取 $-\infty$，softmax 沿知识位置计算。

掩码使无效位置获得零权重，其余位置按相容性分数归一化。$M_i$ 是加到分数上的数学掩码，$\mathbf m_i$ 是知识序列使用的掩码表示，两者表达相同的位置排除关系；字段映射 $M(f)$ 则用于观测到实体的转换。

式 (15) 是自由能最优解的直接计算形式。各分支通过自己的 Query 和 Key 得到 $\alpha^*$，随后使用这些权重聚合 Value。

从信息投影角度，若 $p^0=\operatorname{softmax}(-\epsilon_{im})$ 表示补齐序列上施加位置掩码之前的能量分布，则相同解可写为：

$$
\alpha_{im}^{*}
=\arg\min_{\alpha\in\Delta(J_i)}
D_{\mathrm{KL}}(\alpha\Vert p^0).
$$

其含义是将 $p^0$ 限制到有效支持 $J_i$，再归一化为概率分布。该信息投影的对象是知识位置权重，与原模态特征向量 $\mathbf h_{im}$ 分别对应分布空间与特征空间。

### 3.3.6 多头知识读出

各注意力头使用对应的最优权重读取 Value，再拼接和映射：

$$
\begin{aligned}
\mathbf z_{im}^{kg}
&=W_m^O\operatorname{Concat}_{a=1}^{H}\left(
\sum_{j\in J_i}
\operatorname{DropAttn}(\alpha_{im}^{(a)*})_j
v_{imj}^{(a)}
\right)+b_m^O.
\end{aligned}
\tag{16}
$$

对应英文稿：`eq:knowledge_response`。

$a$ 是注意力头索引，$H$ 是头数；$\alpha_{im}^{(a)*}$ 和 $v_{imj}^{(a)}$ 是第 $a$ 个头的权重与 Value；Concat 将各头的读出向量拼接；$W_m^O,b_m^O$ 将拼接结果映射为与模态表征维度一致的知识响应。

$\operatorname{DropAttn}$ 在训练时对注意力权重施加 dropout，推理时为恒等映射。式 (14) 的最优性对应 dropout 之前的权重。多头读出让不同表示子空间分别聚合知识，再形成统一的分支响应。

空知识输入使用首个零输入占位进行读出，该位置在 dropout 前的注意力权重为 1，得到的响应继续进入相同残差更新。式 (13)–(15) 描述有效实体支持上的知识分配，空输入按上述占位分支处理。

### 3.3.7 残差知识注入

$$
\mathbf h_{im}^{Augmented}
=\mathrm{LayerNorm}\left(
\mathbf h_{im}+\mathbf z_{im}^{kg}
\right).
\tag{17}
$$

对应英文稿：Knowledge readout and residual update 中的残差公式。

$\mathbf h_{im}$ 是原模态表征，$\mathbf z_{im}^{kg}$ 是知识响应，两者维度一致，能够逐元素相加；LayerNorm 对相加后的表征执行层归一化；$\mathbf h_{im}^{Augmented}$ 是知识增强后的输出。

原患者编码沿残差路径保留，读出的知识在同一表示中参与更新。至此，$J_i$ 决定可读取的位置，Key 决定其相容性能量和权重，Value 提供内容，残差公式将这些内容带入后续预测。

### 3.3.8 BM 与 EHR 双向融合

以下融合公式沿用英文稿省略患者索引 $i$ 的写法，各变量均属于同一患者。增强后的 BM 与 EHR 分别查询另一分支：

$$
\begin{aligned}
\mathbf A_{BM\rightarrow ehr}
&=\mathrm{LayerNorm}\left(
\mathbf h_{BM}^{Augmented}
+\mathrm{MCA}(\mathbf Q_{BM},\mathbf K_{ehr},\mathbf V_{ehr})
\right),\\
\mathbf A_{ehr\rightarrow BM}
&=\mathrm{LayerNorm}\left(
\mathbf h_{ehr}^{Augmented}
+\mathrm{MCA}(\mathbf Q_{ehr},\mathbf K_{BM},\mathbf V_{BM})
\right).
\end{aligned}
\tag{18}
$$

对应英文稿：`eq:bidirectional_mca`。

MCA 表示多头交叉注意力模块，$\mathbf Q$、$\mathbf K$、$\mathbf V$ 是增强分支经过学习型映射得到的查询、键和值输入。箭头标记查询方向：第一行由 BM 查询 EHR，第二行由 EHR 查询 BM。$\mathbf A$ 是经过跨分支融合、残差相加和归一化后的输出。

这一步以两组临床分支的整体表征为单位交换信息。知识先通过式 (17) 增强各分支，再随增强表征参与临床融合。

### 3.3.9 联合临床表示

$$
\mathbf H_{ab}
=P_{ab}\left(
\left[
\mathrm{Squeeze}(\mathbf A_{BM\rightarrow ehr})
\parallel
\mathrm{Squeeze}(\mathbf A_{ehr\rightarrow BM})
\right]\right).
\tag{19}
$$

对应英文稿：`eq:hab_def`。

$\parallel$ 表示特征维度拼接；Squeeze 去除单个 token 对应的长度为 1 的维度，保留患者与特征维度；$P_{ab}$ 是联合临床映射，将双向输出转换为 $\mathbf H_{ab}$。下标 $ab$ 标记 BM 与 EHR 两分支融合得到的联合表示。

该公式将两个查询方向的结果组织为一个临床向量，供后续与 MRI 表征融合。

### 3.3.10 MRI 与临床表示融合

$$
\mathbf Z_{mri}
=\mathrm{LayerNorm}\left(
\mathbf h_{mri}^{Augmented}
+\mathrm{MCA}(\mathbf Q_{mri},\mathbf H_{ab},\mathbf H_{ab})
\right).
\tag{20}
$$

对应英文稿：`eq:mri_alignment`。

$\mathbf Q_{mri}$ 来自增强后的 MRI 表征，$\mathbf H_{ab}$ 作为交叉注意力模块的 Key 和 Value 输入；$\mathbf Z_{mri}$ 是将联合临床信息与 MRI 残差表征融合后的输出。

同一临床表示在模块中分别承担 Key 输入与 Value 输入角色，并通过各自的学习型映射参与计算。该阶段连接互补影像信息与已经包含知识响应的临床表征。

### 3.3.11 最终表示拼接

$$
\mathbf F_{final}
=\left[
\mathrm{Squeeze}(\mathbf H_{ab})
\parallel
\mathrm{Squeeze}(\mathbf Z_{mri})
\right].
\tag{21}
$$

对应英文稿：`eq:final_fusion`。

$\mathbf F_{final}$ 是分类器使用的联合特征，包含联合临床表示与临床融合后的 MRI 表示。Squeeze 统一单 token 的张量形状，拼接保留两组表征供最终分类器共同使用。

### 3.3.12 类别概率

MLP 分类器将 $\mathbf F_{final}$ 映射为类别 logits，再计算：

$$
\hat y_{i,c}
=\frac{\exp(z_{i,c})}
{\sum_{j=1}^{C}\exp(z_{i,j})}.
\tag{22}
$$

对应英文稿：`eq:softmax`。

$z_{i,c}$ 是患者 $i$ 在类别 $c$ 上的 logit，$\hat y_{i,c}$ 是预测概率，$C$ 是类别数；分母中的 $j$ 在此索引类别。Softmax 将全部类别 logits 归一化，使概率和为 1。

分类 logit $z_{i,c}$ 是标量，知识响应 $\mathbf z_{im}^{kg}$ 是向量，两者分别属于最终类别预测和中间知识注入阶段。

### 3.3.13 分类交叉熵

$$
\mathcal L_{CE}
=-\frac{1}{B}\sum_{i=1}^{B}\sum_{c=1}^{C}
y_{i,c}\log\hat y_{i,c}.
\tag{23}
$$

对应英文稿：`eq:cross_entropy`。

$B$ 是患者批次大小，$y_{i,c}$ 是 one-hot 真实标签，$\hat y_{i,c}$ 是预测概率。对于每个患者，只有真实类别对应的标签项为 1，其损失为真实类别预测概率的负对数；随后在批次内取平均。

分类监督经融合表示、残差更新和知识读取路径学习网络参数，使患者表征与知识使用方式共同服务于分类任务。

### 3.3.14 分类训练总目标

$$
\mathcal L_{KAMT}
=\mathcal L_{CE}
+\lambda\sum_{w\in\theta}w^2.
\tag{24}
$$

对应英文稿：`eq:total_loss`。

$\theta$ 表示分类网络的可学习参数，$w$ 遍历其中的标量参数，$\lambda$ 是 $L_2$ 正则化系数。交叉熵提供分类监督，平方和项对参数幅度施加代价，整个目标通过 Adam 优化。

方法中三个优化关系对应不同对象：式 (4) 学习图谱实体与关系嵌入，式 (13) 在每次前向计算中确定当前知识权重，式 (24) 学习分类网络参数。条件自由能的解通过 Value 读出、残差更新与多模态融合参与分类，形成从 DemRKG 关系知识到最终预测的连续计算路径。
