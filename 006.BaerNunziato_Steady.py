'''

 

19.07.2017

'''

# ------ LIBRARIES ------ #
from fenics          import *
from mshr            import *

# ------ SIMULATION PARAMETERS ------ #
foldername = 'results.Pgrad_Separation_Galerkin'

# ------ TMIXER GEOMETRY PARAMETERS ------ #
mesh_res  = 100
mesh_P0   = 0.0
mesh_DD   = 0.010          # largura para otimizacao
mesh_L    = 0.050          # 100mm
mesh_Cx   = mesh_L *0.25   # initial circle
mesh_Cy   = mesh_DD*0.5
mesh_Rad  = mesh_DD*0.2
mesh_tol  = mesh_DD*0.01

# ------ TMIXER GEOMETRY PARAMETERS ------ #
cons_rh1 = 1.0E+3
cons_rh2 = 1.2E+3
cons_mu1 = 1.0E-3
cons_mu2 = 1.1E-3
cons_vin = 1.0E-3
cons_kk  = 1.0E-3
cons_g   = 1.0E-3

GENERAL_TOL = 1E-6
TRANSIENT_MAX_ITE = 100

a_min = 0
a_max = 1
v_max = cons_vin*10
p_max = 1.0E5

# ------ MESH ------ #
part1 = Rectangle(
   Point(mesh_P0, mesh_P0),
   Point(mesh_L , mesh_DD)    )
part2 = Circle(
   Point(mesh_Cx, mesh_Cy),
   mesh_Rad                   )
channel = part1 #-part2
mesh = generate_mesh(channel, mesh_res)

# ------ BOUNDARIES DEFINITION ------ #
inlet  = '( on_boundary && near(x[0],'+str(mesh_P0)+') && (x[1]>'+str(mesh_P0)+') && (x[1]<'+str(mesh_DD)+') )'
outlet = '( on_boundary && near(x[0],'+str(mesh_L )+') && (x[1]>'+str(mesh_P0)+') && (x[1]<'+str(mesh_DD)+') )'
walls  = 'on_boundary && !'+inlet+'&& !'+outlet

ds_inlet, ds_walls, ds_outlet = 1,2,3

boundaries     = FacetFunction ('size_t', mesh)
side_inlet     = CompiledSubDomain( inlet    )
side_outlet    = CompiledSubDomain( outlet   )
side_walls     = CompiledSubDomain( walls    )
boundaries.set_all(0)
side_inlet.mark   (boundaries, ds_inlet  )
side_walls.mark   (boundaries, ds_walls  )
side_outlet.mark  (boundaries, ds_outlet )
ds = Measure( 'ds', subdomain_data=boundaries )

# ------ VARIATIONAL FORMULATION ------ #
FE_u  = VectorElement('P', 'triangle', 2)
FE_p  = FiniteElement('P', 'triangle', 1)
FE_a  = FiniteElement('P', 'triangle', 1)
U_prs = FunctionSpace(mesh, FE_p)
U_vel = FunctionSpace(mesh, FE_u)
U_vol = FunctionSpace(mesh, FE_a)
U     = FunctionSpace(mesh, MixedElement([FE_a, FE_u, FE_u, FE_p, FE_p]) )

ans   = Function(U)

a1,u1,u2,p1,p2 = split(ans)
b1,v1,v2,q1,q2 = TestFunctions(U)

N1       = Constant(1         )
KK       = Constant(cons_kk   )
RH1      = Constant(cons_rh1  )
RH2      = Constant(cons_rh2  )
MU1      = Constant(cons_mu1  )
MU2      = Constant(cons_mu2  )
u_inlet  = Constant(cons_vin  )
dl       = Constant(1E-7)
G        = Constant(cons_g)
GG       = as_vector(   [Constant(0), -G]  )
HH       = as_vector(   [Constant(0), Expression('x[1]',degree=2)]   )
NN       = FacetNormal(mesh)

u_in  = as_vector(   [Constant(cons_vin), Constant(0)]   )
u_wl  = as_vector(   [Constant(0),        Constant(0)]   )

a2 = N1 -a1

sigma1 = MU1*(grad(u1)+grad(u1).T) -p1*Identity(len(u1))
sigma2 = MU1*(grad(u2)+grad(u2).T) -p2*Identity(len(u2))

SIGMA1_DS = as_tensor([  [-RH1*a1*inner(GG,HH),  Constant(0)],
                         [ Constant(0), -RH1*a1*inner(GG,HH)]  ])
SIGMA2_DS = as_tensor([  [-RH2*a2*inner(GG,HH),  Constant(0)],
                         [ Constant(0), -RH2*a2*inner(GG,HH)]  ])

u_int = (u1*RH1*a1 + u2*RH2*a2)/(RH1*a1 + RH2*a2)
p_int = p1*a1 + p2*a2

# F12   = MU1*MU2/(MU1+MU2)*(u2_md -u1_md)/dl +(an1*an2*grad(pn2 -pn1)+am1*am2*grad(pm2 -pm1))
# F21   = MU1*MU2/(MU1+MU2)*(u1_md -u2_md)/dl +(an1*an2*grad(pn1 -pn2)+am1*am2*grad(pm1 -pm2))

F12   = MU1*MU2/(MU1+MU2)*(u2 -u1)/dl +p_int*grad(a1)
F21   = MU1*MU2/(MU1+MU2)*(u1 -u2)/dl +p_int*grad(a2)


F1 = inner(u_int, grad(a1)) *b1              *dx \
   - a1*a2*(p1 -p2)*b1*KK                    *dx \
   \
   + div(a1*u1) *q1                          *dx \
   \
   + div(a2*u2) *q2                          *dx \
   \
   + RH1*inner(div(a1*outer(u1,u1)),v1)      *dx \
   + inner(sigma1*a1, grad(v1))              *dx \
   - inner(F12,v1)                           *dx \
   - inner(RH1*a1*GG,v1)                     *dx \
   - inner(dot(SIGMA1_DS,NN), v1)            *ds(ds_outlet) \
   \
   + RH2*inner(div(a2*outer(u2,u2)),v2)*0.5  *dx \
   + inner(sigma2*a2, grad(v2))              *dx \
   - inner(F21,v2)                           *dx \
   - inner(RH2*a2*GG,v2)                     *dx \
   - inner(dot(SIGMA2_DS,NN), v2)            *ds(ds_outlet) \
   \


# ------ BOUNDARY CONDITIONS ------ #
p_aa,p_u1,p_u2,p_p1,p_p2 = 0,1,2,3,4
BC1 = [
         DirichletBC(U.sub(p_aa), Constant(      0.5   ), inlet   ),
         DirichletBC(U.sub(p_u1), Constant((cons_vin,0)), inlet   ),
         DirichletBC(U.sub(p_u2), Constant((cons_vin,0)), inlet   ),
         DirichletBC(U.sub(p_u1), Constant((      0,0 )), walls   ),
         DirichletBC(U.sub(p_u2), Constant((      0,0 )), walls   ),
      ] # end - BC #

# ------ NON LINEAR PROBLEM DEFINITIONS ------ #
lowBound = project(Constant((a_min, -v_max, -v_max, -v_max, -v_max, -p_max, -p_max)), U)
uppBound = project(Constant((a_max, +v_max, +v_max, +v_max, +v_max, +p_max, +p_max)), U)

dF1 = derivative(F1, ans )
nlProblem1 = NonlinearVariationalProblem(F1, ans, BC1, dF1)
nlProblem1.set_bounds(lowBound,uppBound)
nlSolver1  = NonlinearVariationalSolver(nlProblem1)
nlSolver1.parameters["nonlinear_solver"] = "snes"

prm = nlSolver1.parameters["snes_solver"]
prm["error_on_nonconvergence"       ] = True
prm["solution_tolerance"            ] = 1.0E-16
prm["maximum_iterations"            ] = 100
prm["maximum_residual_evaluations"  ] = 20000
prm["absolute_tolerance"            ] = 6.0E-7
prm["relative_tolerance"            ] = 6.0E-7
prm["linear_solver"                 ] = "mumps"
#prm["sign"                          ] = "default"
#prm["method"                        ] = "vinewtonssls"
#prm["line_search"                   ] = "bt"
#prm["preconditioner"                ] = "none"
#prm["report"                        ] = True
#prm["krylov_solver"                 ]
#prm["lu_solver"                     ]

#set_log_level(PROGRESS)

# ------ SAVE FILECONFIGURATIONS ------ #
vtk_aa  = File(foldername+'/volume_fraction.pvd')
vtk_ui1 = File(foldername+'/velocity_intrinsic1.pvd')
vtk_ui2 = File(foldername+'/velocity_intrinsic2.pvd')
vtk_pi1 = File(foldername+'/pressure_intrinsic1.pvd')
vtk_pi2 = File(foldername+'/pressure_intrinsic2.pvd')
vtk_u1  = File(foldername+'/velocity_mean1.pvd')
vtk_u2  = File(foldername+'/velocity_mean2.pvd')
vtk_p1  = File(foldername+'/pressure_mean1.pvd')
vtk_p2  = File(foldername+'/pressure_mean2.pvd')

def save_results():
   aa_viz  = project(a1   , U_vol); aa_viz.rename('Fraction','Fraction');  vtk_aa  << aa_viz
   ui1_viz = project(u1   , U_vel); ui1_viz.rename('velocity intrinsic 1','velocity intrinsic 1'); vtk_ui1 << ui1_viz
   ui2_viz = project(u2   , U_vel); ui2_viz.rename('velocity intrinsic 2','velocity intrinsic 2'); vtk_ui2 << ui2_viz
   pi1_viz = project(p1   , U_prs); pi1_viz.rename('pressure intrinsic 1','pressure intrinsic 1'); vtk_pi1 << pi1_viz
   pi2_viz = project(p2   , U_prs); pi2_viz.rename('pressure intrinsic 2','pressure intrinsic 2'); vtk_pi2 << pi2_viz
   u1_viz  = project(u1*a1, U_vel); u1_viz.rename('velocity mean 1','velocity mean 1');  vtk_u1  << u1_viz
   u2_viz  = project(u2*a2, U_vel); u2_viz.rename('velocity mean 2','velocity mean 2');  vtk_u2  << u2_viz
   p1_viz  = project(p1*a1, U_prs); p1_viz.rename('pressure mean 1','pressure mean 1');  vtk_p1  << p1_viz
   p2_viz  = project(p2*a2, U_prs); p2_viz.rename('pressure mean 2','pressure mean 2');  vtk_p2  << p2_viz

def plot_all():
   plot(a1,title='volume_fraction')
   plot(u1,title='velocity_intrinsic1')
   plot(u2,title='velocity_intrinsic2')
   plot(p1,title='pressure_intrinsic1')
   plot(p2,title='pressure_intrinsic2')
   interactive()


# ------ TRANSIENT SIMULATION ------ #
assign(ans.sub(p_aa), project(Constant(0.5         ), U_vol))
assign(ans.sub(p_u1), project(Constant((cons_vin,0)), U_vel))
assign(ans.sub(p_u2), project(Constant((cons_vin,0)), U_vel))
assign(ans.sub(p_p1), project(Constant(1e-1        ), U_prs))
assign(ans.sub(p_p2), project(Constant(1e-1        ), U_prs))


for g_val in [10**(-4+exp/10.0) for exp in range(40)]:
   G.assign(g_val)
   nlSolver1.solve()
   save_results()

