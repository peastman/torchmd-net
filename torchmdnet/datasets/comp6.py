# Copyright Universitat Pompeu Fabra 2020-2023  https://www.compscience.org
# Distributed under the MIT License.
# (See accompanying file README.md file or copy at http://opensource.org/licenses/MIT)

import h5py
import numpy as np
import torch as pt
from torch_geometric.data import Data, Dataset, download_url
from torchmdnet.datasets.memdataset import MemmappedDataset
from tqdm import tqdm
import os

"""
COmprehensive Machine-learning Potential (COMP6) Benchmark Suite

For more details check:
  - https://arxiv.org/pdf/1801.09319.pdf
  - https://github.com/isayev/COMP6
  - https://aip.scitation.org/doi/abs/10.1063/1.5023802

"""


class COMP6Base(MemmappedDataset):
    ELEMENT_ENERGIES = {
        1: -0.500607632585,
        6: -37.8302333826,
        7: -54.5680045287,
        8: -75.0362229210,
    }  # Copied from ANI-1x
    ATOMIC_NUMBERS = {b"H": 1, b"C": 6, b"N": 7, b"O": 8}
    HARTREE_TO_EV = 27.211386246

    def __init__(
        self,
        root,
        transform=None,
        pre_transform=None,
        pre_filter=None,
    ):
        self.name = self.__class__.__name__
        super().__init__(
            root,
            transform,
            pre_transform,
            pre_filter,
            remove_ref_energy=False,
            properties=("y", "neg_dy"),
        )

    @property
    def raw_url_name(self):
        return self.__class__.__name__

    @property
    def raw_url(self):
        url_prefix = "https://raw.githubusercontent.com/isayev/COMP6/master/COMP6v1"
        return [
            f"{url_prefix}/{self.raw_url_name}/{name}" for name in self.raw_file_names
        ]

    @staticmethod
    def compute_reference_energy(atomic_numbers):
        atomic_numbers = np.array(atomic_numbers)
        energy = sum(COMP6Base.ELEMENT_ENERGIES[z] for z in atomic_numbers)
        return energy * COMP6Base.HARTREE_TO_EV

    def download(self):
        for url in self.raw_url:
            download_url(url, self.raw_dir)

    def sample_iter(self, mol_ids=False):
        for path in tqdm(self.raw_paths, desc="Files"):
            molecules = list(h5py.File(path).values())[0].items()

            for mol_id, mol in tqdm(molecules, desc="Molecules", leave=False):
                z = pt.tensor(
                    [self.ATOMIC_NUMBERS[atom] for atom in mol["species"]],
                    dtype=pt.long,
                )
                all_pos = pt.tensor(mol["coordinates"][:], dtype=pt.float32)
                all_y = pt.tensor(
                    mol["energies"][:] * self.HARTREE_TO_EV, dtype=pt.float64
                )
                all_neg_dy = pt.tensor(
                    mol["forces"][:] * self.HARTREE_TO_EV, dtype=pt.float32
                )
                all_y -= self.compute_reference_energy(z)

                assert all_pos.shape[0] == all_y.shape[0]
                assert all_pos.shape[1] == z.shape[0]
                assert all_pos.shape[2] == 3

                assert all_neg_dy.shape[0] == all_y.shape[0]
                assert all_neg_dy.shape[1] == z.shape[0]
                assert all_neg_dy.shape[2] == 3

                for pos, y, neg_dy in zip(all_pos, all_y, all_neg_dy):
                    # Create a sample
                    args = dict(z=z, pos=pos, y=y.view(1, 1), neg_dy=neg_dy)
                    if mol_ids:
                        args["mol_id"] = f"{os.path.basename(path)}_{mol_id}"
                    data = Data(**args)

                    if self.pre_filter is not None and not self.pre_filter(data):
                        continue

                    if self.pre_transform is not None:
                        data = self.pre_transform(data)

                    yield data


class ANIMD(COMP6Base):
    """
    ANI Molecular Dynamics (ANI-MD) Benchmark. Forces from the ANI-1x potential are
    applied to run 1ns of vacuum molecular dynamics with a 0.25 fs time step at 300 K using
    the Langevin thermostat on 14 well-known drug molecules and two small proteins. System
    sizes range from 20 to 312 atoms. A random subsample of 128 frames from each 1ns
    trajectory is selected, and reference DFT single point calculations are performed to obtain
    QM energies and forces.

    The description copied from https://arxiv.org/pdf/1801.09319.pdf
    """

    @property
    def raw_url_name(self):
        return "ANI-MD"

    @property
    def raw_file_names(self):
        return ["ani_md_bench.h5"]

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def download(self):
        super().download()

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def process(self):
        super().process()


class DrugBank(COMP6Base):
    """
    DrugBank Benchmark. This benchmark is developed through a subsampling of the
    DrugBank database of real drug molecules. 837 SMILES strings containing C, N, and O
    are randomly selected. Like the GDB7to9 benchmark, the molecules are embedded in 3D
    space, structurally optimized, and normal modes are computed. DNMS is utilized to
    generate random non-equilibrium conformations.

    The description copied from https://arxiv.org/pdf/1801.09319.pdf
    """

    @property
    def raw_file_names(self):
        return ["drugbank_testset.h5"]

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def download(self):
        super().download()

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def process(self):
        super().process()


class GDB07to09(COMP6Base):
    """
    GDB7to9 Benchmark. The GDB-11 subsets containing 7 to 9 heavy atoms (C, N, and O)
    are subsampled and randomly embedded in 3D space using RDKit [www.rdkit.org]. A total
    of 1500 molecule SMILES [opensmiles.org] strings are selected: 500 per 7, 8, and 9 heavyatom set. The resulting structures are optimized with tight convergence criteria, and normal
    modes/force constants are computed using the reference DFT model. Finally, diverse
    normal mode sampling (DNMS) is carried out to generate non-equilibrium conformations.

    The description copied from https://arxiv.org/pdf/1801.09319.pdf
    """

    @property
    def raw_file_names(self):
        return ["gdb11_07_test500.h5", "gdb11_08_test500.h5", "gdb11_09_test500.h5"]

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def download(self):
        super().download()

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def process(self):
        super().process()


class GDB10to13(COMP6Base):
    """
    GDB10to13 Benchmark. Subsamples of 500 SMILES strings each from the 10 and 11
    heavy-atom subsets of GDB-11 and 1000 SMILES strings from the 12 and 13 heavyatom subsets of the GDB-13 database are randomly selected. DNMS is utilized to
    generate random non-equilibrium conformations.

    The description copied from https://arxiv.org/pdf/1801.09319.pdf
    """

    @property
    def raw_file_names(self):
        return [
            "gdb11_10_test500.h5",
            "gdb11_11_test500.h5",
            "gdb13_12_test1000.h5",
            "gdb13_13_test1000.h5",
        ]

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def download(self):
        super().download()

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def process(self):
        super().process()


class Tripeptides(COMP6Base):
    """
    Tripeptide Benchmark. 248 random tripeptides containing H, C, N, and O are generated
    using FASTA strings and randomly embedded in 3D space using RDKit. As with
    GDB7to9, the molecules are optimized, and normal modes are computed. DNMS is utilized
    to generate random non-equilibrium conformations.

    The description copied from https://arxiv.org/pdf/1801.09319.pdf
    """

    @property
    def raw_file_names(self):
        return ["tripeptide_full.h5"]

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def download(self):
        super().download()

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def process(self):
        super().process()


class S66X8(COMP6Base):
    """
    S66x8 Benchmark. This dataset is built from the original S66x850 benchmark for
    comparing accuracy between different methods in describing noncovalent interactions
    common in biological molecules. S66x8 is developed from 66 dimeric systems involving
    hydrogen bonding, pi-pi stacking, London interactions, and mixed influence interactions.
    While the keen reader might question the use of this benchmark without dispersion
    corrections, since dispersion corrections such as the D3 correction by Grimme et al. are
    a posteriori additions to the produced energy, then a comparison without the correction is
    equivalent to a comparison with the same dispersion corrections applied to both models.

    The description copied from https://arxiv.org/pdf/1801.09319.pdf
    """

    @property
    def raw_url_name(self):
        return "s66x8"

    @property
    def raw_file_names(self):
        return ["s66x8_wb97x6-31gd.h5"]

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def download(self):
        super().download()

    # Circumvent https://github.com/pyg-team/pytorch_geometric/issues/4567
    # TODO remove when fixed
    def process(self):
        super().process()


class COMP6v1(Dataset):
    """
    Superset of all COMP6 subsets (ANI-MD, DrugBank, GDB7to9, GDB10to13, Tripeptides, S66x8)
    """

    def __init__(
        self,
        root,
        transform=None,
        pre_transform=None,
        pre_filter=None,
    ):
        super().__init__(root, transform, pre_transform, pre_filter)

        self.subsets = [
            DS(root, transform, pre_transform, pre_filter)
            for DS in (ANIMD, DrugBank, GDB07to09, GDB10to13, Tripeptides, S66X8)
        ]

        self.num_samples = sum(len(subset) for subset in self.subsets)

        self.subset_indices = []
        for i_subset, subset in enumerate(self.subsets):
            for i_sample in range(len(subset)):
                self.subset_indices.append([i_subset, i_sample])
        self.subset_indices = np.array(self.subset_indices)

    def len(self):
        return self.num_samples

    def get(self, idx):
        i_subset, i_sample = self.subset_indices[idx]
        return self.subsets[i_subset][i_sample]
