// JS Compartido Global de la Plataforma LatinPyme
document.addEventListener("DOMContentLoaded", () => {
    console.log("LatinPyme Platform JS Inicializado correctamente.");
});

// Helper para SweetAlert simplificado
const AlertHelper = {
    success(title, text) {
        Swal.fire({
            icon: 'success',
            title: title,
            text: text,
            confirmButtonColor: '#4f46e5',
            timer: 3000,
            timerProgressBar: true
        });
    },
    error(title, text) {
        Swal.fire({
            icon: 'error',
            title: title,
            text: text,
            confirmButtonColor: '#ef4444'
        });
    },
    loading(title, text) {
        Swal.fire({
            title: title,
            text: text,
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });
    },
    close() {
        Swal.close();
    }
};
