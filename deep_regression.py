import utils, teachers 
import torch.nn as nn
from theory import compute_theory
import os 

start_time = utils.time.time()
args = utils.parseArguments()
if args.L >1 and args.act == "erf":
	print("\nI cannot compute predicted gen error of an erf multilayer network")
	args.compute_theory = False 
device = utils.find_device(args.device)
P = args.P
print('\nNumber of examples in the train set:', P)
home = utils.os.environ['HOME']
trainsetFilename = "dummy"
#CREATION OF MACRO FOLDERS
mother_dir = './runs/prova/'
utils.make_directory(mother_dir)
first_subdir = mother_dir + f'teacher_{args.teacher_type}_net_{args.L}hl_opt_{args.opt}_actf_{args.act}/'
utils.make_directory(first_subdir)
theoryFilename = f"{first_subdir}theory_N_{args.N}_lambda0_{args.lambda0}_lambda1_{args.lambda1}.txt"
if not os.path.isfile(theoryFilename):
	f = open(theoryFilename,"a")
	print('#P', 'N1', 'Qbar', 'pred error', file = f)
	f.close()
#CREATION OF FOLDERS
attributes_string = f'lr_{args.lr}_w_decay_{args.wd}_lambda0_{args.lambda0}_lambda1_{args.lambda1}_'
if args.bs != 0: 
	attributes_string = attributes_string +f'bs_{args.bs}_'
attributes_string = attributes_string + f"{args.L}hl_N0_{args.N}_N_{args.N1}"
run_folder = first_subdir + attributes_string + '/'
utils.make_directory(run_folder)

if args.teacher_type == 'linear': 
	teacher_dir = f'{first_subdir}teachers/'
	utils.make_directory(teacher_dir)
	trainsets_dir = f'{first_subdir}trainsets/'
	utils.make_directory(trainsets_dir)
	teacherFilename = f'{teacher_dir}/teacher_N_{args.N}.pt'
	teacher_class = teachers.linear_dataset()
	teacher_class.resume = args.resume_data
	teacher_class.make_teacher_parameters(args.N, teacherFilename)
	trainsetFilename = f'{trainsets_dir}trainset_N_{args.N}_P_{P}_Ptest_{args.Ptest}.pt'
elif args.teacher_type == 'mnist': 
	teacher_class = teachers.mnist_dataset(args.N)
elif args.teacher_type == 'random': 
	teacher_class = teachers.random_dataset(args.N)
teacher_class.save_data = args.save_data

#BATCH SIZE
if args.bs == 0: 
	batch_size_train = P
	batch_size_test  = min(args.Ptest, P)
else: 
	batch_size_train = args.bs
	batch_size_test = args.bs
teacher_class.batch_size = batch_size_train

#CRREATION OF DADTASET AND THEORY CALCULATION
inputs, targets, test_inputs, test_targets, resumed = teacher_class.make_data(P, args.Ptest, trainsetFilename, device)
inputs, targets, test_inputs, test_targets = inputs.to(device), targets.to(device), test_inputs.to(device), test_targets.to(device),
print("\nTest size",len(test_targets))
if args.compute_theory:
	start_time = utils.time.time()
	gen_error_pred, Qbar = compute_theory(inputs, targets, test_inputs, test_targets, args.N1, args.lambda1, P, args.Ptest, args.lambda0,args.act,args.L,args.device,args.infwidth)
	f = open(theoryFilename, "a")
	print(P,args.N1,Qbar, gen_error_pred, file = f)
	f.close()
	print(f"\nPredicted error is: {gen_error_pred} \ntheory computation took - {utils.time.time() - start_time} seconds -")
	start_time = utils.time.time()

#NET INITIALISATION
print(f'\nsize of hidden layer is: {args.N1}')
net_class = utils.make_MLP(args.N, args.N1, args.L, args.lambda1, args.lambda0)
bias = False
net = net_class.Sequential(bias, args.act)
utils.cuda_init(net, device)	

#TRAINING DYNAMICS SPECIFICATION
if args.opt == 'adam': 
	optimizer = utils.optim.Adam(net.parameters(), lr=args.lr, weight_decay=args.wd)
elif args.opt == 'sgd':
	optimizer = utils.optim.SGD(net.parameters(), lr=args.lr, weight_decay=args.wd)
criterion = nn.MSELoss()
train_args = [net,inputs,targets,criterion,optimizer,batch_size_train]	
test_args = [net,test_inputs,test_targets,criterion,batch_size_test]	
training = utils.train
testing = utils.test

#RUN DYNAMICS
runFilename = f'{run_folder}run_P_{P}_replica_{args.R}.txt'
if not utils.os.path.exists(runFilename):
	sourceFile = open(runFilename, 'a')
	print('#1. epoch', '2. train error', '3. test error', file = sourceFile)
	sourceFile.close()
sourceFile = open(runFilename, 'a')
for epoch in range(args.epochs):
	train_loss = training(*train_args)
	test_loss = testing(*test_args)
	print(epoch, train_loss, test_loss, file = sourceFile)
	if epoch % args.checkpoint == 0 or epoch == args.epochs-1 :
		sourceFile.close()
		sourceFile = open(runFilename, 'a')
		print(f'\nEpoch: {epoch} \nTrain Loss: {train_loss} \nTest Loss: {test_loss} \n training took --- {utils.time.time() - start_time} seconds ---')				
		start_time = utils.time.time()	
sourceFile.close()