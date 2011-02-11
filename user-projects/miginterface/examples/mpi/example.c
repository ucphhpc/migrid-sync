#include <stdio.h>

#include <mpi.h>


int main(int argc, char **argv) {
    int rank, size;

    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD,&size);
    MPI_Comm_rank(MPI_COMM_WORLD,&rank);

    if (argc < 2) {
        fprintf(stderr, "err: missing argument\n");
	MPI_Finalize();
        return -1;
    }

    MPI_Barrier(MPI_COMM_WORLD);

    if (rank==0) {
	printf("All %d processes are ready\n", size);
    }

    MPI_Barrier(MPI_COMM_WORLD);

    printf("rank %d: %s! I'll do my part!!!\n", rank, argv[1]);

    MPI_Finalize();
    return 0;
}
