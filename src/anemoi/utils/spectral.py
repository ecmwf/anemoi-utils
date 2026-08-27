import logging
import einops
import torch
import abc
from torch_dct import dct_2d, idct_2d

LOGGER = logging.getLogger(__name__)


class SpectralTransform(torch.nn.Module):
    """Abstract base class for spectral transforms."""

    @abc.abstractmethod
    def forward(
        self,
        data: torch.Tensor,
        **kwargs,
    ) -> torch.Tensor:
        """Transform data to spectral domain.

        Parameters
        ----------
        data : torch.Tensor
            Input data in the spatial domain of expected shape
            `[batch, dates, ensemble, points, variables]` or `[batch, ensemble, points, variables]`.

        Returns
        -------
        torch.Tensor
            Data transformed to the spectral domain, of shape
            `[batch, dates, ensemble, freq_points, variables]` or `[batch, ensemble, points, variables]`.
        """

class DCT2D(SpectralTransform):
    """2D Discrete Cosine Transform."""

    def __init__(self, x_dim: int, y_dim: int, norm: str | None = None, **kwargs) -> None:
        super().__init__()
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.norm = norm

    def forward(self, data: torch.Tensor) -> torch.Tensor:
        if data.ndim == 5:
            b, t, e, p, v = data.shape
            x = einops.rearrange(
                data,
                "b t e (y x) v -> (b t e v) y x",
                x=self.x_dim,
                y=self.y_dim,
            )
        elif data.ndim == 4:
            b, e, p, v = data.shape
            x = einops.rearrange(
                data,
                "b e (y x) v -> (b e v) y x",
                x=self.x_dim,
                y=self.y_dim,
            )
        else:
            raise ValueError("Argument with incorrect number of dimensions.")
        if p != self.x_dim * self.y_dim:
            ValueError("Grid doesn't fit the transform shape.")

        
        x = dct_2d(x, norm=self.norm)
        if data.ndim == 5:
            return einops.rearrange(x, "(b t e v) y x -> b t e (y x) v", b=b, e=e, v=v, t=t)
        else:
            return einops.rearrange(x, "(b e v) y x -> b e (y x) v", b=b, e=e, v=v)
        
class InverseDCT2D(SpectralTransform):
    """Inverse 2D Discrete Cosine Transform."""

    def __init__(self, x_dim: int, y_dim: int, norm: str | None = None, **kwargs) -> None:
        super().__init__()
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.norm = norm

    def forward(self, data: torch.Tensor) -> torch.Tensor:
        if data.ndim == 5:
            b, t, e, p, v = data.shape
            x = einops.rearrange(
                data,
                "b t e (y x) v -> (b t e v) y x",
                x=self.x_dim,
                y=self.y_dim,
            )
        elif data.ndim == 4:
            b, e, p, v = data.shape
            x = einops.rearrange(
                data,
                "b e (y x) v -> (b e v) y x",
                x=self.x_dim,
                y=self.y_dim,
            )
        else:
            raise ValueError("Argument with incorrect number of dimensions.")
        if p != self.x_dim * self.y_dim:
            ValueError("Grid doesn't fit the transform shape.")

        
        x = idct_2d(x, norm=self.norm)
        if data.ndim == 5:
            return einops.rearrange(x, "(b t e v) y x -> b t e (y x) v", b=b, e=e, v=v, t=t)
        else:
            return einops.rearrange(x, "(b e v) y x -> b e (y x) v", b=b, e=e, v=v)