# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.4'
#       jupytext_version: 1.1.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# # HSMMの性能比較の数値実験

import sys
sys.path.append("../lib")

# +
import math

from IPython.core.display import display, Markdown, Latex
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.special import gammaln, psi
from scipy.stats import norm, t, cauchy, laplace, gumbel_r, gamma, skewnorm, pareto, multivariate_normal, kurtosis, skew
from typing import Callable
from sklearn.mixture import BayesianGaussianMixture
from sklearn.datasets import load_iris, load_wine, load_breast_cancer

from HyperbolicSecantMixtureModelVB import HyperbolicSecantMixtureVB
from learning import GaussianMixtureModelVB
from util import GaussianMixtureModel, HyperbolicSecantMixtureModel, StudentMixtureModel, LaplaceMixtureModel, GumbelMixtureModel
# -

# # 問題設定

# ## 真の分布の設定
# + データ生成分布は変更しますが、混合比, 中心, scaleは同じものを流用

true_ratio = np.array([0.33, 0.33, 0.34])
true_delta = 0
true_s = np.array([[2, 2], [0.5, 0.5], [1, 1]])
true_b = np.array([[2, 4], [-4, -2], [0, 0]])
true_param = dict()
true_param["ratio"] = true_ratio
true_param["mean"] = true_b
true_param["precision"] = true_s
true_param["scale"] = np.array([np.diag(1/np.sqrt(true_s[k,:])) for k in range(len(true_ratio))])
K0 = len(true_ratio)
M = true_b.shape[1]

# ## Learning setting:

# +
### 学習データの数
n = 400

### テストデータの数
N = 10000

### データの出方の個数
ndataset = 1

### 事前分布のハイパーパラメータ
pri_params = {
    "pri_alpha": 0.1,
    "pri_beta": 0.001,
    "pri_gamma": M+2,
    "pri_delta": 1
}

### データ生成の回数
data_seed_start = 201907
data_seeds = np.arange(start = data_seed_start, stop = data_seed_start + ndataset, step = 1)

### 学習モデルの初期値の乱数 -> データseedにoffsetを加えたものを使う
learning_num = 10
learning_seed_offset = 100

### 繰り返しアルゴリズムの繰り返し回数
learning_iteration = 1000

### 学習モデルのコンポーネントの数
K = np.array([5, 3])
# -

# # 性能評価
# + 1連の流れ
#     1. データ生成する
#     1. 学習を行う
#     1. 精度評価を行う
#     1. 1に戻って再度計算

# # コンポーネントの分布が正規分布の場合

# +
gerror_gmm_diag = np.zeros(len(data_seeds))
cklerror_gmm_diag = np.zeros(len(data_seeds))
c01error_gmm_diag = np.zeros(len(data_seeds))

gerror_gmm_cov = np.zeros(len(data_seeds))
cklerror_gmm_cov = np.zeros(len(data_seeds))
c01error_gmm_cov = np.zeros(len(data_seeds))

gerror_hsmm = np.zeros(len(data_seeds))
cklerror_hsmm = np.zeros(len(data_seeds))
c01error_hsmm = np.zeros(len(data_seeds))

for i, data_seed in enumerate(data_seeds):
    ### データを生成する
    (train_X, train_label, train_label_arg) = GaussianMixtureModel.rvs(true_ratio, true_b, true_s, size = n, data_seed = data_seed)
    (test_X, test_label, test_label_arg) = GaussianMixtureModel.rvs(true_ratio, true_b, true_s, size = N)
    
    gmm_diag_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "diag")
    gmm_diag_obj.fit(train_X)
    
    gmm_cov_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "full")
    gmm_cov_obj.fit(train_X)
    
    hsmm_obj = HyperbolicSecantMixtureVB(K = K[0],                                     
                                         pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                         iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset)
    hsmm_obj.fit(train_X)
    posterior_true_logprob = GaussianMixtureModel().latent_posterior_logprob(train_X, true_ratio, true_b, true_s)
    cklerror_gmm_diag[i] = gmm_diag_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_gmm_cov[i] = gmm_cov_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_hsmm[i] = hsmm_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    
    c01error_gmm_diag[i] = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_gmm_cov[i] = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_hsmm[i] = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)
    
    true_empirical_entropy = -GaussianMixtureModel.logpdf(test_X, true_ratio, true_b, true_s)
    gerror_gmm_diag[i] = (-true_empirical_entropy - gmm_diag_obj.predict_logproba(test_X))/len(test_X)
    gerror_gmm_cov[i] = (-true_empirical_entropy - gmm_cov_obj.predict_logproba(test_X))/len(test_X)
    gerror_hsmm[i] = (-true_empirical_entropy - hsmm_obj.predict_logproba(test_X))/len(test_X)
# -


print(f"""
gerror_gmm_diag: {gerror_gmm_diag.mean()},
gerror_gmm_cov: {gerror_gmm_cov.mean()},
gerror_hsmm: {gerror_hsmm.mean()},
cklerror_gmm_diag: {cklerror_gmm_diag.mean()},
cklerror_gmm_cov: {cklerror_gmm_cov.mean()},
cklerror_hsmm: {cklerror_hsmm.mean()},
c01error_gmm_diag: {c01error_gmm_diag.mean()},
c01error_gmm_cov: {c01error_gmm_cov.mean()},
c01error_hsmm: {c01error_hsmm.mean()}
""")

for k in np.unique(train_label_arg):
    train_ind = np.where(train_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])

# +
est_label_prob = gmm_diag_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = np.zeros(len(est_label_arg))
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 2

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = hsmm_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = gmm_cov_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()
# -

# # コンポーネントの分布が双曲線正割分布の場合

# +
gerror_gmm_diag = np.zeros(len(data_seeds))
cklerror_gmm_diag = np.zeros(len(data_seeds))
c01error_gmm_diag = np.zeros(len(data_seeds))

gerror_gmm_cov = np.zeros(len(data_seeds))
cklerror_gmm_cov = np.zeros(len(data_seeds))
c01error_gmm_cov = np.zeros(len(data_seeds))

gerror_hsmm = np.zeros(len(data_seeds))
cklerror_hsmm = np.zeros(len(data_seeds))
c01error_hsmm = np.zeros(len(data_seeds))
for i, data_seed in enumerate(data_seeds):
    ### データを生成する
    (train_X, train_label, train_label_arg) = HyperbolicSecantMixtureModel.rvs(true_ratio, true_b, true_s, size = n, data_seed = data_seed)
    (test_X, test_label, test_label_arg) = HyperbolicSecantMixtureModel.rvs(true_ratio, true_b, true_s, size = N)
    
    gmm_diag_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "diag")
    gmm_diag_obj.fit(train_X)
    
    gmm_cov_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "full")
    gmm_cov_obj.fit(train_X)
    
    hsmm_obj = HyperbolicSecantMixtureVB(K = K[0],                                     
                                         pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                         iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset)
    hsmm_obj.fit(train_X)
    
    posterior_true_logprob = HyperbolicSecantMixtureModel().latent_posterior_logprob(train_X, true_ratio, true_b, true_s)
    cklerror_gmm_diag[i] = gmm_diag_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_gmm_cov[i] = gmm_cov_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_hsmm[i] = hsmm_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    
    c01error_gmm_diag[i] = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_gmm_cov[i] = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_hsmm[i] = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)
    
    true_empirical_entropy = -HyperbolicSecantMixtureModel.logpdf(test_X, true_ratio, true_b, true_s)
    gerror_gmm_diag[i] = (-true_empirical_entropy - gmm_diag_obj.predict_logproba(test_X))/len(test_X)
    gerror_gmm_cov[i] = (-true_empirical_entropy - gmm_cov_obj.predict_logproba(test_X))/len(test_X)
    gerror_hsmm[i] = (-true_empirical_entropy - hsmm_obj.predict_logproba(test_X))/len(test_X)
# -

print(f"""
gerror_gmm_diag: {gerror_gmm_diag.mean()},
gerror_gmm_cov: {gerror_gmm_cov.mean()},
gerror_hsmm: {gerror_hsmm.mean()},
cklerror_gmm_diag: {cklerror_gmm_diag.mean()},
cklerror_gmm_cov: {cklerror_gmm_cov.mean()},
cklerror_hsmm: {cklerror_hsmm.mean()},
c01error_gmm_diag: {c01error_gmm_diag.mean()},
c01error_gmm_cov: {c01error_gmm_cov.mean()},
c01error_hsmm: {c01error_hsmm.mean()}
""")

for k in np.unique(train_label_arg):
    train_ind = np.where(train_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])

# +
est_label_prob = gmm_diag_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = np.zeros(len(est_label_arg))
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 3

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = hsmm_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = gmm_cov_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()
# -

# # コンポーネントの分布がt分布の場合

# +
gerror_gmm_diag = np.zeros(len(data_seeds))
cklerror_gmm_diag = np.zeros(len(data_seeds))
c01error_gmm_diag = np.zeros(len(data_seeds))

gerror_gmm_cov = np.zeros(len(data_seeds))
cklerror_gmm_cov = np.zeros(len(data_seeds))
c01error_gmm_cov = np.zeros(len(data_seeds))

gerror_hsmm = np.zeros(len(data_seeds))
cklerror_hsmm = np.zeros(len(data_seeds))
c01error_hsmm = np.zeros(len(data_seeds))

true_df = 3
for i, data_seed in enumerate(data_seeds):
    ### データを生成する
    (train_X, train_label, train_label_arg) = StudentMixtureModel.rvs(true_ratio, true_b, true_s, size = n, data_seed = data_seed, df = true_df)
    (test_X, test_label, test_label_arg) = StudentMixtureModel.rvs(true_ratio, true_b, true_s, size = N, df = true_df)
    
    gmm_diag_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "diag")
    gmm_diag_obj.fit(train_X)
    
    gmm_cov_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "full")
    gmm_cov_obj.fit(train_X)
    
    hsmm_obj = HyperbolicSecantMixtureVB(K = K[0],                                     
                                         pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                         iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset)
    hsmm_obj.fit(train_X)
    
    posterior_true_logprob = StudentMixtureModel().latent_posterior_logprob(train_X, true_ratio, true_b, true_s, df = true_df)
    cklerror_gmm_diag[i] = gmm_diag_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_gmm_cov[i] = gmm_cov_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_hsmm[i] = hsmm_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    
    c01error_gmm_diag[i] = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_gmm_cov[i] = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_hsmm[i] = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)
    
    true_empirical_entropy = -StudentMixtureModel.logpdf(test_X, true_ratio, true_b, true_s, df = true_df)
    gerror_gmm_diag[i] = (-true_empirical_entropy - gmm_diag_obj.predict_logproba(test_X))/len(test_X)
    gerror_gmm_cov[i] = (-true_empirical_entropy - gmm_cov_obj.predict_logproba(test_X))/len(test_X)
    gerror_hsmm[i] = (-true_empirical_entropy - hsmm_obj.predict_logproba(test_X))/len(test_X)
# -

print(f"""
gerror_gmm_diag: {gerror_gmm_diag.mean()},
gerror_gmm_cov: {gerror_gmm_cov.mean()},
gerror_hsmm: {gerror_hsmm.mean()},
cklerror_gmm_diag: {cklerror_gmm_diag.mean()},
cklerror_gmm_cov: {cklerror_gmm_cov.mean()},
cklerror_hsmm: {cklerror_hsmm.mean()},
c01error_gmm_diag: {c01error_gmm_diag.mean()},
c01error_gmm_cov: {c01error_gmm_cov.mean()},
c01error_hsmm: {c01error_hsmm.mean()}
""")

for k in np.unique(train_label_arg):
    train_ind = np.where(train_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])

# +
est_label_prob = gmm_diag_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = np.zeros(len(est_label_arg))
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = hsmm_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = gmm_cov_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()
# -

# # コンポーネントの分布がt分布の場合

data_seeds = [201909]

# +
gerror_gmm_diag = np.zeros(len(data_seeds))
cklerror_gmm_diag = np.zeros(len(data_seeds))
c01error_gmm_diag = np.zeros(len(data_seeds))

gerror_gmm_cov = np.zeros(len(data_seeds))
cklerror_gmm_cov = np.zeros(len(data_seeds))
c01error_gmm_cov = np.zeros(len(data_seeds))

gerror_hsmm = np.zeros(len(data_seeds))
cklerror_hsmm = np.zeros(len(data_seeds))
c01error_hsmm = np.zeros(len(data_seeds))

true_df = 1.9
for i, data_seed in enumerate(data_seeds):
    ### データを生成する
    (train_X, train_label, train_label_arg) = StudentMixtureModel.rvs(true_ratio, true_b, true_s, size = n, data_seed = data_seed, df = true_df)
    (test_X, test_label, test_label_arg) = StudentMixtureModel.rvs(true_ratio, true_b, true_s, size = N, df = true_df)
    
    gmm_diag_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "diag")
    gmm_diag_obj.fit(train_X)
    
    gmm_cov_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "full")
    gmm_cov_obj.fit(train_X)
    
    hsmm_obj = HyperbolicSecantMixtureVB(K = K[0],                                     
                                         pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                         iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset)
    hsmm_obj.fit(train_X)
    
    posterior_true_logprob = StudentMixtureModel().latent_posterior_logprob(train_X, true_ratio, true_b, true_s, df = true_df)
    cklerror_gmm_diag[i] = gmm_diag_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_gmm_cov[i] = gmm_cov_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_hsmm[i] = hsmm_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    
    c01error_gmm_diag[i] = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_gmm_cov[i] = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_hsmm[i] = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)
    
    true_empirical_entropy = -StudentMixtureModel.logpdf(test_X, true_ratio, true_b, true_s, df = true_df)
    gerror_gmm_diag[i] = (-true_empirical_entropy - gmm_diag_obj.predict_logproba(test_X))/len(test_X)
    gerror_gmm_cov[i] = (-true_empirical_entropy - gmm_cov_obj.predict_logproba(test_X))/len(test_X)
    gerror_hsmm[i] = (-true_empirical_entropy - hsmm_obj.predict_logproba(test_X))/len(test_X)
# -

print(f"""
gerror_gmm_diag: {gerror_gmm_diag.mean()},
gerror_gmm_cov: {gerror_gmm_cov.mean()},
gerror_hsmm: {gerror_hsmm.mean()},
cklerror_gmm_diag: {cklerror_gmm_diag.mean()},
cklerror_gmm_cov: {cklerror_gmm_cov.mean()},
cklerror_hsmm: {cklerror_hsmm.mean()},
c01error_gmm_diag: {c01error_gmm_diag.mean()},
c01error_gmm_cov: {c01error_gmm_cov.mean()},
c01error_hsmm: {c01error_hsmm.mean()}
""")

for k in np.unique(train_label_arg):
    train_ind = np.where(train_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])

# +
est_label_prob = gmm_diag_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = np.zeros(len(est_label_arg))
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 3
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 4

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = hsmm_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 3
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 4
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = gmm_cov_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 3
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 4

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()
# -

# # コンポーネントの分布がラプラス分布の場合

# +
gerror_gmm_diag = np.zeros(len(data_seeds))
cklerror_gmm_diag = np.zeros(len(data_seeds))
c01error_gmm_diag = np.zeros(len(data_seeds))

gerror_gmm_cov = np.zeros(len(data_seeds))
cklerror_gmm_cov = np.zeros(len(data_seeds))
c01error_gmm_cov = np.zeros(len(data_seeds))

gerror_hsmm = np.zeros(len(data_seeds))
cklerror_hsmm = np.zeros(len(data_seeds))
c01error_hsmm = np.zeros(len(data_seeds))

for i, data_seed in enumerate(data_seeds):
    ### データを生成する
    (train_X, train_label, train_label_arg) = LaplaceMixtureModel.rvs(true_ratio, true_b, true_s, size = n, data_seed = data_seed)
    (test_X, test_label, test_label_arg) = LaplaceMixtureModel.rvs(true_ratio, true_b, true_s, size = N)
    
    gmm_diag_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "diag")
    gmm_diag_obj.fit(train_X)
    
    gmm_cov_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "full")
    gmm_cov_obj.fit(train_X)
    
    hsmm_obj = HyperbolicSecantMixtureVB(K = K[0],                                     
                                         pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                         iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset)
    hsmm_obj.fit(train_X)
    
    posterior_true_logprob = LaplaceMixtureModel().latent_posterior_logprob(train_X, true_ratio, true_b, true_s)
    cklerror_gmm_diag[i] = gmm_diag_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_gmm_cov[i] = gmm_cov_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_hsmm[i] = hsmm_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    
    c01error_gmm_diag[i] = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_gmm_cov[i] = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_hsmm[i] = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)
    
    true_empirical_entropy = -LaplaceMixtureModel.logpdf(test_X, true_ratio, true_b, true_s)
    gerror_gmm_diag[i] = (-true_empirical_entropy - gmm_diag_obj.predict_logproba(test_X))/len(test_X)
    gerror_gmm_cov[i] = (-true_empirical_entropy - gmm_cov_obj.predict_logproba(test_X))/len(test_X)
    gerror_hsmm[i] = (-true_empirical_entropy - hsmm_obj.predict_logproba(test_X))/len(test_X)
# -

print(f"""
gerror_gmm_diag: {gerror_gmm_diag.mean()},
gerror_gmm_cov: {gerror_gmm_cov.mean()},
gerror_hsmm: {gerror_hsmm.mean()},
cklerror_gmm_diag: {cklerror_gmm_diag.mean()},
cklerror_gmm_cov: {cklerror_gmm_cov.mean()},
cklerror_hsmm: {cklerror_hsmm.mean()},
c01error_gmm_diag: {c01error_gmm_diag.mean()},
c01error_gmm_cov: {c01error_gmm_cov.mean()},
c01error_hsmm: {c01error_hsmm.mean()}
""")

for k in np.unique(train_label_arg):
    train_ind = np.where(train_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])

# +
est_label_prob = gmm_diag_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = np.zeros(len(est_label_arg))
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 3
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 4
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 1

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = hsmm_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 3
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 4

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = gmm_cov_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 3
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 4
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 2

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()
# -

# # コンポーネントの分布がガンベル分布の場合

# +
gerror_gmm_diag = np.zeros(len(data_seeds))
cklerror_gmm_diag = np.zeros(len(data_seeds))
c01error_gmm_diag = np.zeros(len(data_seeds))

gerror_gmm_cov = np.zeros(len(data_seeds))
cklerror_gmm_cov = np.zeros(len(data_seeds))
c01error_gmm_cov = np.zeros(len(data_seeds))

gerror_hsmm = np.zeros(len(data_seeds))
cklerror_hsmm = np.zeros(len(data_seeds))
c01error_hsmm = np.zeros(len(data_seeds))

for i, data_seed in enumerate(data_seeds):
    ### データを生成する
    (train_X, train_label, train_label_arg) = GumbelMixtureModel.rvs(true_ratio, true_b, true_s, size = n, data_seed = data_seed)
    (test_X, test_label, test_label_arg) = GumbelMixtureModel.rvs(true_ratio, true_b, true_s, size = N)
    
    gmm_diag_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "diag")
    gmm_diag_obj.fit(train_X)
    
    gmm_cov_obj = GaussianMixtureModelVB(K = K[0],
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset, method = "full")
    gmm_cov_obj.fit(train_X)
    
    hsmm_obj = HyperbolicSecantMixtureVB(K = K[0],                                     
                                         pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                         iteration = 1000, restart_num=learning_num, learning_seed=data_seed + learning_seed_offset)
    hsmm_obj.fit(train_X)
    
    posterior_true_logprob = GumbelMixtureModel().latent_posterior_logprob(train_X, true_ratio, true_b, true_s)
    cklerror_gmm_diag[i] = gmm_diag_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_gmm_cov[i] = gmm_cov_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    cklerror_hsmm[i] = hsmm_obj.score_latent_kl(posterior_true_logprob)[0]/len(train_X)
    
    c01error_gmm_diag[i] = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_gmm_cov[i] = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
    c01error_hsmm[i] = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)
    
    true_empirical_entropy = -GumbelMixtureModel.logpdf(test_X, true_ratio, true_b, true_s)
    gerror_gmm_diag[i] = (-true_empirical_entropy - gmm_diag_obj.predict_logproba(test_X))/len(test_X)
    gerror_gmm_cov[i] = (-true_empirical_entropy - gmm_cov_obj.predict_logproba(test_X))/len(test_X)
    gerror_hsmm[i] = (-true_empirical_entropy - hsmm_obj.predict_logproba(test_X))/len(test_X)
# -

print(f"""
gerror_gmm_diag: {gerror_gmm_diag.mean()},
gerror_gmm_cov: {gerror_gmm_cov.mean()},
gerror_hsmm: {gerror_hsmm.mean()},
cklerror_gmm_diag: {cklerror_gmm_diag.mean()},
cklerror_gmm_cov: {cklerror_gmm_cov.mean()},
cklerror_hsmm: {cklerror_hsmm.mean()},
c01error_gmm_diag: {c01error_gmm_diag.mean()},
c01error_gmm_cov: {c01error_gmm_cov.mean()},
c01error_hsmm: {c01error_hsmm.mean()}
""")

for k in np.unique(train_label_arg):
    train_ind = np.where(train_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])

np.unique(est_label_arg)

# +
est_label_prob = gmm_diag_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = np.zeros(len(est_label_arg))
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 3
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 4

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()

# +
est_label_prob = hsmm_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 0

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()
# -

np.unique(est_label_arg)

# +
est_label_prob = gmm_cov_obj.result_["u_xi"]
est_label_arg = np.argmax(est_label_prob, axis = 1)

### 色をtrueと揃えるための処理
fitted_est_label_arg = est_label_arg.copy()
fitted_est_label_arg[np.where(est_label_arg == 0)[0]] = 3
fitted_est_label_arg[np.where(est_label_arg == 1)[0]] = 0
fitted_est_label_arg[np.where(est_label_arg == 2)[0]] = 2
fitted_est_label_arg[np.where(est_label_arg == 3)[0]] = 1
fitted_est_label_arg[np.where(est_label_arg == 4)[0]] = 4

for k in np.unique(fitted_est_label_arg):
    train_ind = np.where(fitted_est_label_arg == k)[0]
    plt.scatter(train_X[train_ind,0], train_X[train_ind,1])
plt.show()
# -

# # For real data
# + Fisher's iris data are used.
# + generalization loss and 01 loss are calculated here.

skew(total_X)

kurtosis(total_X)

total_X.std(axis = 0)

total_X.mean(axis = 0)

for k in np.unique(train_label_arg):
    print(kurtosis(total_X[np.where(train_label_arg == k)[0],:]))

# +
# データを生成する
data = load_iris()
total_data = data.data
total_X = total_data**3
mean_val = total_data.mean(axis = 0)
std_val = total_data.std(axis = 0)
# total_X = ((total_data - mean_val)/std_val)**2

n = 150
N = total_X.shape[0] - n
shuffled_ind = np.random.permutation(n + N)
train_ind = shuffled_ind[:n]
test_ind = shuffled_ind[n:]

train_X = total_X[train_ind,:]
train_label_arg = data.target[train_ind]
test_X = total_X[test_ind,:]
test_label_arg = data.target[test_ind,]
n, M = train_X.shape

gmm_diag_obj = GaussianMixtureModelVB(K = K[0],
                                 pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                 iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset, method = "diag")
gmm_diag_obj.fit(train_X)

gmm_cov_obj = GaussianMixtureModelVB(K = K[0],
                                 pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = M+2, pri_delta = pri_params["pri_delta"], 
                                 iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset, method = "full")
gmm_cov_obj.fit(train_X)

hsmm_obj = HyperbolicSecantMixtureVB(K = K[0],                                     
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset)
hsmm_obj.fit(train_X)

c01error_gmm_diag = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
c01error_gmm_cov = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
c01error_hsmm = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)

# gerror_gmm_diag = - gmm_diag_obj.predict_logproba(test_X)/len(test_X)
# gerror_gmm_cov=  - gmm_cov_obj.predict_logproba(test_X)/len(test_X)
# gerror_hsmm = - hsmm_obj.predict_logproba(test_X)/len(test_X)
# -

print(f"""
c01error_gmm_diag: {c01error_gmm_diag},
c01error_gmm_cov: {c01error_gmm_cov},
c01error_hsmm: {c01error_hsmm}
""")

# # For real data
# + wine data are used.
# + generalization loss and 01 loss are calculated here.

for k in np.unique(train_label_arg):
    print(kurtosis(total_X[np.where(train_label_arg == k)[0],:]))

# +
# データを生成する
data = load_wine()
total_data = data.data
mean_val = total_data.mean(axis = 0)
std_val = total_data.std(axis = 0)
total_X = (total_data - mean_val)/std_val
# total_X = total_X

n = 150
N = total_X.shape[0] - n
shuffled_ind = np.random.permutation(n + N)
train_ind = shuffled_ind[:n]
test_ind = shuffled_ind[n:]

train_X = total_X[train_ind,:]
train_label_arg = data.target[train_ind]
test_X = total_X[test_ind,:]
test_label_arg = data.target[test_ind,]
n, M = train_X.shape

gmm_diag_obj = GaussianMixtureModelVB(K = K[0],
                                 pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                 iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset, method = "diag")
gmm_diag_obj.fit(train_X)

gmm_cov_obj = GaussianMixtureModelVB(K = K[0],
                                 pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = M+2, pri_delta = pri_params["pri_delta"], 
                                 iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset, method = "full")
gmm_cov_obj.fit(train_X)

hsmm_obj = HyperbolicSecantMixtureVB(K = K[0],                                     
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset)
hsmm_obj.fit(train_X)

c01error_gmm_diag = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
c01error_gmm_cov = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
c01error_hsmm = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)

gerror_gmm_diag = - gmm_diag_obj.predict_logproba(test_X)/len(test_X)
gerror_gmm_cov=  - gmm_cov_obj.predict_logproba(test_X)/len(test_X)
gerror_hsmm = - hsmm_obj.predict_logproba(test_X)/len(test_X)
# -

print(f"""
gerror_gmm_diag: {gerror_gmm_diag},
gerror_gmm_cov: {gerror_gmm_cov},
gerror_hsmm: {gerror_hsmm},
c01error_gmm_diag: {c01error_gmm_diag},
c01error_gmm_cov: {c01error_gmm_cov},
c01error_hsmm: {c01error_hsmm}
""")

# # For real data
# + breast cancer data
# + generalization loss and 01 loss are calculated here.

# +
# データを生成する
data = load_breast_cancer()
total_data = data.data
total_X = total_data
mean_val = total_data.mean(axis = 0)
std_val = total_data.std(axis = 0)
total_X = (total_data - mean_val)/std_val

n = 400
N = total_X.shape[0] - n
shuffled_ind = np.random.permutation(n + N)
train_ind = shuffled_ind[:n]
test_ind = shuffled_ind[n:]

train_X = total_X[train_ind,:]
train_label_arg = data.target[train_ind]
test_X = total_X[test_ind,:]
test_label_arg = data.target[test_ind,]
n, M = train_X.shape

gmm_diag_obj = GaussianMixtureModelVB(K = K[1],
                                 pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                 iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset, method = "diag")
gmm_diag_obj.fit(train_X)

gmm_cov_obj = GaussianMixtureModelVB(K = K[1],
                                 pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = M + 2, pri_delta = pri_params["pri_delta"], 
                                 iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset, method = "full")
gmm_cov_obj.fit(train_X)

hsmm_obj = HyperbolicSecantMixtureVB(K = K[1],                                     
                                     pri_alpha = pri_params["pri_alpha"], pri_beta = pri_params["pri_beta"], pri_gamma = pri_params["pri_gamma"], pri_delta = pri_params["pri_delta"], 
                                     iteration = 1000, restart_num=learning_num, learning_seed=data_seed_start + learning_seed_offset)
hsmm_obj.fit(train_X)

c01error_gmm_diag = gmm_diag_obj.score_clustering(train_label_arg)[0]/len(train_X)
c01error_gmm_cov = gmm_cov_obj.score_clustering(train_label_arg)[0]/len(train_X)
c01error_hsmm = hsmm_obj.score_clustering(train_label_arg)[0]/len(train_X)

gerror_gmm_diag = - gmm_diag_obj.predict_logproba(test_X)/len(test_X)
gerror_gmm_cov=  - gmm_cov_obj.predict_logproba(test_X)/len(test_X)
gerror_hsmm = - hsmm_obj.predict_logproba(test_X)/len(test_X)
# -

print(f"""
gerror_gmm_diag: {gerror_gmm_diag},
gerror_gmm_cov: {gerror_gmm_cov},
gerror_hsmm: {gerror_hsmm},
c01error_gmm_diag: {c01error_gmm_diag},
c01error_gmm_cov: {c01error_gmm_cov},
c01error_hsmm: {c01error_hsmm}
""")
