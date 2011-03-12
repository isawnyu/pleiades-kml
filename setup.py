from setuptools import setup, find_packages

version = '0.8.2'

setup(name='pleiades.kml',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Framework :: Zope3",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='Sean Gillies',
      author_email='sgillies@frii.com',
      url='http://svn.plone.org/svn/plone/plone.example',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['pleiades'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'pleiades.geographer',
          'zgeo.plone.kml'
          ],
      tests_require=[
          'pleiades.workspace'
          ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
