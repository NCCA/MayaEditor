"""Sample Python code for testing."""

import maya.cmds as cmds


class SceneManager:
    """Manages Maya scene operations."""

    def __init__(self):
        """Initialize the scene manager."""
        self.scene_name = "untitled"

    def create_sphere(self, name="mySphere", radius=1.0):
        """Create a polygon sphere in the scene.

        Parameters
        ----------
        name : str
            Name for the sphere
        radius : float
            Radius of the sphere

        Returns
        -------
        str
            Name of the created sphere transform node
        """
        sphere = cmds.polySphere(name=name, radius=radius)
        return sphere[0]

    def create_cube(self, name="myCube", width=1.0):
        """Create a polygon cube in the scene.

        Parameters
        ----------
        name : str
            Name for the cube
        width : float
            Width of the cube sides

        Returns
        -------
        str
            Name of the created cube transform node
        """
        cube = cmds.polyCube(name=name, width=width, height=width, depth=width)
        return cube[0]


def batch_create_spheres(count=10):
    """Create multiple spheres in a grid pattern.

    Parameters
    ----------
    count : int
        Number of spheres to create

    Returns
    -------
    list
        List of created sphere names
    """
    manager = SceneManager()
    spheres = []

    for i in range(count):
        name = f"sphere_{i:03d}"
        sphere = manager.create_sphere(name=name, radius=0.5)
        spheres.append(sphere)

        # Position in grid
        x = (i % 5) * 2.0
        z = (i // 5) * 2.0
        cmds.move(x, 0, z, sphere)

    return spheres
