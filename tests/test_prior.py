import gpflow
import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
import pytest


np.random.seed(1)

class Datum:
    X = 10 * np.random.randn(5,1)
    Y = 10 * np.random.randn(5,1)
    lengthscale = 3.3


def test_gpr_objective_equivalence():
    """
    In Maximum Likelihood Estimation (MLE), i.e. when there are no priors on
    the parameters, the objective should not depend on any transforms on the
    parameters.
    We use GPR as a simple model that has an objective.
    """
    data = (Datum.X, Datum.Y)
    l_value = Datum.lengthscale

    l_variable = tf.Variable(l_value, dtype=gpflow.default_float(), trainable=True)
    m1 = gpflow.models.GPR(data, kernel=gpflow.kernels.SquaredExponential(lengthscale=l_value))
    m2 = gpflow.models.GPR(data, kernel=gpflow.kernels.SquaredExponential())
    m2.kernel.lengthscale = gpflow.Parameter(l_variable, transform=None)
    assert np.allclose(m1.kernel.lengthscale.numpy(),
                       m2.kernel.lengthscale.numpy())  # consistency check

    assert np.allclose(m1.neg_log_marginal_likelihood().numpy(),
                       m2.neg_log_marginal_likelihood().numpy()), \
            "MLE objective should not depend on Parameter transform"


def test_log_prior_with_no_prior():
    """
    A parameter without any prior should have zero log-prior,
    even if it has a transform to constrain it.
    """
    param = gpflow.Parameter(5.3, transform=gpflow.positive())
    assert param.log_prior().numpy() == 0.0



def fix_dtype(x):
    # TODO replace with generic function for handling tensorflow_probability ...
    return tf.cast(x, gpflow.default_float())

class DummyModel(gpflow.models.BayesianModel):
    value = 3.3
    log_scale = 0.4

    def __init__(self, with_transform):
        super().__init__()

        prior = tfp.distributions.Normal(fix_dtype(1.0), fix_dtype(1.0))

        scale = np.exp(self.log_scale)
        if with_transform:
            transform = tfp.bijectors.AffineScalar(scale=fix_dtype(scale))
        else:
            transform = None

        self.theta = gpflow.Parameter(self.value, prior=prior, transform=transform)

    def log_likelihood(self):
        return (self.theta + 5) ** 2

def test_map_contains_log_det_jacobian():
    m1 = DummyModel(with_transform=True)
    m2 = DummyModel(with_transform=False)
    assert np.allclose(- m1.neg_log_marginal_likelihood().numpy(),
                       - m2.neg_log_marginal_likelihood().numpy() + m1.log_scale), \
            "MAP objective should differ by log|Jacobian| of the transform"